import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Self, TypeGuard, get_args

import httpx

ReviewStatus = Literal["running", "failed", "finished"]

StoredReviewStatus = Literal["scheduled", "running", "failed", "finished"]
_ALLOWED_STATUSES = frozenset(get_args(StoredReviewStatus))


def is_stored_review_status(value: object) -> TypeGuard[StoredReviewStatus]:
    return isinstance(value, str) and value in _ALLOWED_STATUSES


class ReviewStateError(RuntimeError):
    pass


class TransientReviewStateError(ReviewStateError):
    pass


class ReviewStateConfigurationError(ReviewStateError):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ReviewStateProtocolError(ReviewStateError):
    """The web service response does not match the worker API contract"""


class PermanentReviewStateError(ReviewStateError):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class ReviewStateClient:
    base_url: str
    token: str
    max_attempts: int = 4
    transport: httpx.AsyncBaseTransport | None = field(default=None, repr=False)
    sleep: Callable[[float], Awaitable[None]] = field(default=asyncio.sleep, repr=False)
    _client: httpx.AsyncClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=10,
            headers={"Authorization": f"Bearer {self.token}"},
            transport=self.transport,
        )

    async def set_state(
        self,
        review_id: str,
        status: ReviewStatus,
        *,
        result: dict[str, Any] | None = None,
        error: str | None = None,
        usage: dict[str, Any] | None = None,
        cost: dict[str, Any] | None = None,
        completed_at: datetime | None = None,
    ) -> StoredReviewStatus:
        payload: dict[str, Any] = {
            "status": status,
        }

        if result is not None:
            payload["result"] = result

        if error is not None:
            payload["error"] = error

        if usage is not None:
            payload["usage"] = usage

        if cost is not None:
            payload["cost"] = cost

        if completed_at is not None:
            payload["completed_at"] = completed_at.isoformat()

        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                response = await self._client.patch(
                    f"/api/v1/internal/reviews/{review_id}/state",
                    json=payload,
                )
            except httpx.TransportError as exc:
                last_error = exc
            else:
                status_code = response.status_code
                if 200 <= status_code < 300:
                    try:
                        current_status = response.json()["review"]["status"]
                    except (KeyError, TypeError, ValueError) as exc:
                        raise ReviewStateProtocolError(
                            "Web service returned an invalid review state response."
                        ) from exc

                    if not is_stored_review_status(current_status):
                        raise ReviewStateProtocolError(
                            "Web service returned an invalid review status."
                        )

                    return current_status

                message = f"Web service returned HTTP {status_code}."
                if status_code in {401, 403}:
                    raise ReviewStateConfigurationError(
                        message, status_code=status_code
                    )
                if status_code in {408, 425, 429} or status_code >= 500:
                    last_error = TransientReviewStateError(message)
                elif 400 <= status_code < 500:
                    raise PermanentReviewStateError(message, status_code=status_code)
                else:
                    raise ReviewStateProtocolError(message)

            if attempt + 1 < self.max_attempts:
                await self.sleep(0.5 * (2**attempt))

        raise TransientReviewStateError(
            "Could not persist review state."
        ) from last_error

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()
