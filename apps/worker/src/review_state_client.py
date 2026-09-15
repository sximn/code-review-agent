import asyncio
from dataclasses import dataclass, field
from typing import Any, Literal, Self

import httpx

ReviewStatus = Literal["running", "failed", "finished"]
StoredReviewStatus = Literal["scheduled", "running", "failed", "finished"]


class ReviewStateError(RuntimeError):
    pass


@dataclass
class ReviewStateClient:
    base_url: str
    token: str
    max_attempts: int = 4
    _client: httpx.AsyncClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=10,
            headers={"Authorization": f"Bearer {self.token}"},
        )

    async def set_state(
        self,
        review_id: str,
        status: ReviewStatus,
        *,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> StoredReviewStatus:
        payload: dict[str, Any] = {"reviewId": review_id, "status": status}
        if result is not None:
            payload["result"] = result
        if error is not None:
            payload["error"] = error

        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                response = await self._client.patch(
                    "/api/internal/reviews/state",
                    json=payload,
                )
                if response.status_code < 500:
                    response.raise_for_status()
                    current_status = response.json()["review"]["status"]
                    if current_status not in {
                        "scheduled",
                        "running",
                        "failed",
                        "finished",
                    }:
                        raise ReviewStateError(
                            "Web service returned an invalid review status."
                        )
                    return current_status

                last_error = ReviewStateError(
                    f"Web service returned HTTP {response.status_code}."
                )
            except (httpx.TransportError, KeyError, ValueError) as exc:
                last_error = exc

            if attempt + 1 < self.max_attempts:
                await asyncio.sleep(0.5 * (2**attempt))

        raise ReviewStateError("Could not persist review state.") from last_error

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()
