import httpx
import pytest
from src.review_state_client import ReviewStateClient


@pytest.mark.asyncio
async def test_set_state_retries_server_error() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1

        # fake error on first attempt -> test that 2 calls were attempted and a single delay was recorded
        if attempts == 1:
            return httpx.Response(503, request=request)

        return httpx.Response(
            200,
            request=request,
            json={"review": {"status": "finished"}},
        )

    delays: list[float] = []

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)

    async with ReviewStateClient(
        "https://example.test",
        "token",
        transport=httpx.MockTransport(handler),
        sleep=fake_sleep,
    ) as client:
        status = await client.set_state("review-1", "finished")

    assert status == "finished"
    assert attempts == 2
    assert delays == [0.5]
