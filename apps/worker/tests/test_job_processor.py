import asyncio
import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock

import pytest
from src.completion import ReviewCompletion
from src.completion_store import CompletionStore
from src.config import AppConfig
from src.job_processor import JobProcessor
from src.processing_types import (
    InvalidCheckpointError,
    ProcessingOutcome,
    QueueMessage,
    StorageError,
)
from src.review_execution import ReviewExecutor, ReviewSession
from src.review_state_client import (
    PermanentReviewStateError,
    ReviewStateClient,
    ReviewStateConfigurationError,
    ReviewStateProtocolError,
    TransientReviewStateError,
)


def assert_not_finalized(store):
    store.acknowledge.assert_not_awaited()
    store.dead_letter.assert_not_awaited()


@pytest.mark.asyncio
class TestJobProcessor:
    @pytest.fixture
    def config(self, make_config) -> AppConfig:
        return make_config(review_job_name="review", completion_max_delivery_attempts=3)

    @pytest.fixture
    def message(self):
        return QueueMessage(
            "123-0",
            {
                "job_id": "job-1",
                "type": "review",
                "payload": json.dumps(
                    {
                        "repository": "owner/repo",
                        "pull_request": 2,
                        "visibility": "public",
                    }
                ),
            },
        )

    @pytest.fixture
    def completion(self):
        return ReviewCompletion(status="finished", result={"summary": "OK"})

    @pytest.fixture
    def store(self, completion):
        store = Mock(spec=CompletionStore)
        store.load = AsyncMock(return_value=completion)
        store.save = AsyncMock()
        store.record_delivery_failure = AsyncMock(
            return_value=completion.model_copy(
                update={"delivery_attempts": 1, "last_delivery_error": "unavailable"}
            )
        )
        store.acknowledge = AsyncMock()
        store.dead_letter = AsyncMock()
        return store

    @pytest.fixture
    def state(self):
        state = Mock(spec=ReviewStateClient)
        state.set_state = AsyncMock(return_value="finished")
        return state

    @pytest.fixture
    def events(self) -> list[str]:
        return []

    @pytest.fixture
    def session(self, completion):
        session = Mock(spec=ReviewSession)
        session.run = AsyncMock(return_value=completion)
        return session

    @pytest.fixture
    def executor(self, session, events):
        executor = Mock(spec=ReviewExecutor)

        @asynccontextmanager
        async def opened(job_id: str) -> AsyncGenerator[ReviewSession, None]:
            events.append("open")
            try:
                yield session
            finally:
                events.append("cleanup")

        # open() returns an async context manager; it is not awaited directly.
        executor.open = Mock(side_effect=opened)
        return executor

    @pytest.fixture
    def processor(self, config, store, executor, state):
        return JobProcessor(
            config=config,
            store=store,
            executor=executor,
            state_client=state,
        )

    async def test_checkpoint_reuse_skips_execution_and_acknowledges_delivery(
        self, processor, message, completion, executor, state, store
    ):
        outcome = await processor.process(message)

        assert outcome == ProcessingOutcome.ACKNOWLEDGED
        executor.open.assert_not_called()
        state.set_state.assert_awaited_once_with(
            "job-1", "finished", **completion.state_kwargs()
        )
        store.acknowledge.assert_awaited_once_with(message, job_id="job-1")
        store.dead_letter.assert_not_awaited()

    async def test_new_review_is_saved_before_cleanup_and_delivery(
        self, processor, message, completion, store, state, session, events
    ):
        store.load.return_value = None

        async def set_state(job_id, status, **kwargs):
            events.append(status)
            return status

        async def run(payload):
            events.append("run")
            return completion

        async def save(job_id, completion):
            events.append("save")

        async def ack(*args, **kwargs):
            events.append("ack")

        state.set_state.side_effect = set_state
        session.run.side_effect = run
        store.save.side_effect = save
        store.acknowledge.side_effect = ack

        outcome = await processor.process(message)

        assert outcome == ProcessingOutcome.ACKNOWLEDGED
        assert events == [
            "running",
            "open",
            "run",
            "save",
            "cleanup",
            "finished",
            "ack",
        ]
        store.save.assert_awaited_once_with("job-1", completion)

    async def test_already_terminal_receiver_skips_execution(
        self, processor, message, store, state, executor
    ):
        store.load.return_value = None
        state.set_state.return_value = "finished"

        assert await processor.process(message) == ProcessingOutcome.ACKNOWLEDGED

        executor.open.assert_not_called()
        store.save.assert_not_awaited()
        store.acknowledge.assert_awaited_once_with(message, job_id="job-1")

    async def test_failed_execution_completion_is_saved_and_delivered(
        self, processor, message, store, session, state
    ):
        store.load.return_value = None
        failed = ReviewCompletion(status="failed", error="Agent crashed")
        session.run.return_value = failed
        state.set_state.side_effect = ["running", "failed"]

        assert await processor.process(message) == ProcessingOutcome.ACKNOWLEDGED

        store.save.assert_awaited_once_with("job-1", failed)
        state.set_state.assert_any_await("job-1", "failed", **failed.state_kwargs())

    async def test_transient_delivery_failure_records_attempt_and_leaves_pending(
        self, processor, message, state, store, executor
    ):
        state.set_state.side_effect = TransientReviewStateError("unavailable")

        assert await processor.process(message) == ProcessingOutcome.RETRY_PENDING

        store.record_delivery_failure.assert_awaited_once_with("job-1", "unavailable")
        assert_not_finalized(store)
        executor.open.assert_not_called()

    async def test_exhausted_delivery_goes_to_dlq_without_separate_ack(
        self, processor, message, state, store, completion
    ):
        state.set_state.side_effect = TransientReviewStateError("unavailable")
        exhausted = completion.model_copy(update={"delivery_attempts": 3})
        store.record_delivery_failure.return_value = exhausted

        assert await processor.process(message) == ProcessingOutcome.DEAD_LETTERED

        store.dead_letter.assert_awaited_once()
        kwargs = store.dead_letter.await_args.kwargs
        assert kwargs["phase"] == "delivery"
        assert kwargs["completion"] == exhausted
        store.acknowledge.assert_not_awaited()

    async def test_permanent_delivery_rejection_goes_to_dlq(
        self, processor, message, state, store
    ):
        state.set_state.side_effect = PermanentReviewStateError(
            "HTTP 422", status_code=422
        )

        assert await processor.process(message) == ProcessingOutcome.DEAD_LETTERED

        store.dead_letter.assert_awaited_once()
        assert store.dead_letter.await_args.kwargs["phase"] == "delivery"
        assert "422" in store.dead_letter.await_args.kwargs["reason"]
        store.acknowledge.assert_not_awaited()

    async def test_transient_start_failure_leaves_pending_without_execution(
        self, processor, message, store, state, executor
    ):
        store.load.return_value = None
        state.set_state.side_effect = TransientReviewStateError("offline")

        assert await processor.process(message) == ProcessingOutcome.RETRY_PENDING

        executor.open.assert_not_called()
        assert_not_finalized(store)

    @pytest.mark.parametrize(
        "error",
        [
            ReviewStateConfigurationError("HTTP 401", status_code=401),
            ReviewStateProtocolError("invalid response"),
        ],
    )
    async def test_systemic_web_failure_leaves_pending_without_finalizing(
        self, processor, message, state, store, executor, error
    ):
        state.set_state.side_effect = error

        assert await processor.process(message) == ProcessingOutcome.RETRY_PENDING

        executor.open.assert_not_called()
        store.record_delivery_failure.assert_not_awaited()
        assert_not_finalized(store)

    async def test_permanent_start_failure_goes_to_dlq_without_execution(
        self, processor, message, store, state, executor
    ):
        store.load.return_value = None
        state.set_state.side_effect = PermanentReviewStateError(
            "HTTP 404", status_code=404
        )

        assert await processor.process(message) == ProcessingOutcome.DEAD_LETTERED

        executor.open.assert_not_called()
        store.dead_letter.assert_awaited_once()
        assert store.dead_letter.await_args.kwargs["phase"] == "start"
        store.acknowledge.assert_not_awaited()

    async def test_corrupt_checkpoint_preserves_original_data_in_dlq(
        self, processor, message, store, state, executor
    ):
        store.load.side_effect = InvalidCheckpointError("broken-json")

        assert await processor.process(message) == ProcessingOutcome.DEAD_LETTERED

        store.dead_letter.assert_awaited_once()
        assert store.dead_letter.await_args.kwargs["raw_completion"] == "broken-json"
        assert store.dead_letter.await_args.kwargs["phase"] == "checkpoint"
        state.set_state.assert_not_awaited()
        executor.open.assert_not_called()

    async def test_missing_job_id_is_dead_lettered(self, processor, store, state):
        message = QueueMessage("124-0", {"type": "review"})

        assert await processor.process(message) == ProcessingOutcome.DEAD_LETTERED

        store.dead_letter.assert_awaited_once()
        assert store.dead_letter.await_args.args[0] == message
        assert store.dead_letter.await_args.kwargs["job_id"] is None
        state.set_state.assert_not_awaited()

    async def test_unknown_job_type_is_dead_lettered(
        self, processor, message, store, executor
    ):
        message = QueueMessage("124-0", {**message.fields, "type": "unknown"})

        assert await processor.process(message) == ProcessingOutcome.DEAD_LETTERED

        store.dead_letter.assert_awaited_once()
        executor.open.assert_not_called()

    async def test_malformed_json_is_dead_lettered(
        self, processor, message, store, state
    ):
        store.load.return_value = None
        message = QueueMessage("124-0", {**message.fields, "payload": "{"})

        assert await processor.process(message) == ProcessingOutcome.DEAD_LETTERED

        store.dead_letter.assert_awaited_once()
        state.set_state.assert_not_awaited()

    async def test_valid_json_with_invalid_review_payload_creates_failed_completion(
        self, processor, message, store, state, executor
    ):
        store.load.return_value = None
        state.set_state.return_value = "failed"
        message = QueueMessage("124-0", {**message.fields, "payload": "{}"})

        assert await processor.process(message) == ProcessingOutcome.ACKNOWLEDGED

        executor.open.assert_not_called()
        store.save.assert_awaited_once()
        saved = store.save.await_args.args[1]
        assert saved.status == "failed"
        assert saved.error
        state.set_state.assert_awaited_once_with(
            "job-1", "failed", **saved.state_kwargs()
        )

    async def test_existing_checkpoint_does_not_need_valid_payload(
        self, processor, executor
    ):
        message = QueueMessage("124-0", {"job_id": "job-1", "type": "review"})

        assert await processor.process(message) == ProcessingOutcome.ACKNOWLEDGED

        executor.open.assert_not_called()

    async def test_checkpoint_read_failure_leaves_pending(
        self, processor, message, store, state
    ):
        store.load.side_effect = StorageError("Redis offline")

        assert await processor.process(message) == ProcessingOutcome.RETRY_PENDING

        assert_not_finalized(store)
        state.set_state.assert_not_awaited()

    async def test_checkpoint_save_failure_does_not_deliver_or_ack(
        self, processor, message, store, state, events
    ):
        store.load.return_value = None
        state.set_state.return_value = "running"
        store.save.side_effect = StorageError("Redis offline")

        assert await processor.process(message) == ProcessingOutcome.RETRY_PENDING

        assert state.set_state.await_count == 1
        assert_not_finalized(store)
        assert "cleanup" in events

    async def test_attempt_save_failure_does_not_ack_or_dead_letter(
        self, processor, message, state, store
    ):
        state.set_state.side_effect = TransientReviewStateError("offline")
        store.record_delivery_failure.side_effect = StorageError("Redis offline")

        assert await processor.process(message) == ProcessingOutcome.RETRY_PENDING

        assert_not_finalized(store)

    async def test_dlq_failure_leaves_pending(self, processor, message, state, store):
        state.set_state.side_effect = PermanentReviewStateError("422")
        store.dead_letter.side_effect = StorageError("DLQ unavailable")

        assert await processor.process(message) == ProcessingOutcome.RETRY_PENDING

        store.acknowledge.assert_not_awaited()

    async def test_ack_failure_leaves_checkpoint_for_retry(
        self, processor, message, store
    ):
        store.acknowledge.side_effect = StorageError("ACK unavailable")

        assert await processor.process(message) == ProcessingOutcome.RETRY_PENDING

        store.dead_letter.assert_not_awaited()

    async def test_cancellation_propagates_and_does_not_finalize(
        self, processor, message, state, store
    ):
        state.set_state.side_effect = asyncio.CancelledError()

        with pytest.raises(asyncio.CancelledError):
            await processor.process(message)

        assert_not_finalized(store)

    async def test_unexpected_error_propagates_without_ack(
        self, processor, message, state, store
    ):
        state.set_state.side_effect = RuntimeError("programming bug")

        with pytest.raises(RuntimeError, match="programming bug"):
            await processor.process(message)

        assert_not_finalized(store)
