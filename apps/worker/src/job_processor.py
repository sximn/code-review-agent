import json
import logging

from pydantic import ValidationError

from .completion import ReviewCompletion
from .completion_store import CompletionStore
from .config import AppConfig
from .processing_types import (
    InvalidCheckpointError,
    ProcessingOutcome,
    QueueMessage,
    StorageError,
)
from .repository import ReviewRequestPayload
from .review_execution import ReviewExecutor
from .review_state_client import (
    PermanentReviewStateError,
    ReviewStateClient,
    TransientReviewStateError,
)

logger = logging.getLogger(__name__)


class JobProcessor:
    def __init__(
        self,
        config: AppConfig,
        store: CompletionStore,
        executor: ReviewExecutor,
        state_client: ReviewStateClient,
    ) -> None:
        self.config = config
        self.store = store
        self.executor = executor
        self.state_client = state_client

    async def process(self, message: QueueMessage) -> ProcessingOutcome:
        try:
            return await self._process(message)
        except StorageError:
            logger.exception(
                "Storage unavailable; leaving message pending: %s", message.message_id
            )
            return ProcessingOutcome.RETRY_PENDING
        # Cancellation and programming errors intentionally propagate.

    async def _dead_letter(
        self,
        message: QueueMessage,
        job_id: str | None,
        *,
        phase: str,
        reason: str,
        completion: ReviewCompletion | None = None,
        raw_completion: str | None = None,
    ) -> ProcessingOutcome:
        await self.store.dead_letter(
            message,
            job_id=job_id,
            phase=phase,
            reason=reason,
            completion=completion,
            raw_completion=raw_completion,
        )
        return ProcessingOutcome.DEAD_LETTERED

    async def _process(self, message: QueueMessage) -> ProcessingOutcome:
        fields = message.fields
        job_id = fields.get("job_id") or None
        if job_id is None or not fields.get("type"):
            return await self._dead_letter(
                message,
                job_id,
                phase="validation",
                reason="Job message is missing required fields.",
            )
        if fields["type"] != self.config.review_job_name:
            return await self._dead_letter(
                message,
                job_id,
                phase="validation",
                reason=f"Unknown job type: {fields['type']}",
            )
        try:
            completion = await self.store.load(job_id)
        except InvalidCheckpointError as exc:
            return await self._dead_letter(
                message,
                job_id,
                phase="checkpoint",
                reason=str(exc),
                raw_completion=exc.raw_completion,
            )
        if completion is not None:
            return await self._deliver_completion(message, job_id, completion)

        try:
            raw_payload = json.loads(fields["payload"])
        except (KeyError, json.JSONDecodeError):
            return await self._dead_letter(
                message,
                job_id,
                phase="validation",
                reason="Job message is missing a payload or valid JSON.",
            )
        if not isinstance(raw_payload, dict):
            return await self._dead_letter(
                message,
                job_id,
                phase="validation",
                reason="Job payload must be a JSON object.",
            )
        try:
            payload = ReviewRequestPayload.model_validate(raw_payload)
        except ValidationError:
            completion = ReviewCompletion(
                status="failed", error="The queued review payload is invalid."
            )
            await self.store.save(job_id, completion)
        else:
            try:
                current_status = await self.state_client.set_state(job_id, "running")
            except PermanentReviewStateError as exc:
                return await self._dead_letter(
                    message, job_id, phase="start", reason=str(exc)
                )
            except TransientReviewStateError:
                return ProcessingOutcome.RETRY_PENDING
            if current_status in {"failed", "finished"}:
                await self.store.acknowledge(message, job_id=job_id)
                return ProcessingOutcome.ACKNOWLEDGED
            async with self.executor.open(job_id) as session:
                completion = await session.run(payload)
                await self.store.save(job_id, completion)
        return await self._deliver_completion(message, job_id, completion)

    async def _deliver_completion(
        self, message: QueueMessage, job_id: str, completion: ReviewCompletion
    ) -> ProcessingOutcome:
        try:
            await self.state_client.set_state(
                job_id, completion.status, **completion.state_kwargs()
            )
        except PermanentReviewStateError as exc:
            saved = await self.store.record_delivery_failure(job_id, str(exc))
            return await self._dead_letter(
                message, job_id, phase="delivery", reason=str(exc), completion=saved
            )
        except TransientReviewStateError as exc:
            saved = await self.store.record_delivery_failure(job_id, str(exc))
            if saved.delivery_attempts >= self.config.completion_max_delivery_attempts:
                return await self._dead_letter(
                    message,
                    job_id,
                    phase="delivery",
                    reason=f"Completion delivery exhausted {saved.delivery_attempts} attempts: {exc}",
                    completion=saved,
                )
            return ProcessingOutcome.RETRY_PENDING
        await self.store.acknowledge(message, job_id=job_id)
        return ProcessingOutcome.ACKNOWLEDGED
