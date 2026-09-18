import json

import httpx
import pytest
from src.review_state_client import ReviewStateClient, ReviewStateError


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


@pytest.mark.asyncio
async def test_valid_retry_count():
    with pytest.raises(ValueError, match="max_attempts"):
        _ = ReviewStateClient("https://example.test", "token", max_attempts=0)


@pytest.mark.parametrize(
    "result,error,expected_dynamic_fields",
    [
        (None, "Error when reviewing", {"error": "Error when reviewing"}),
        ({"hello": "world"}, None, {"result": {"hello": "world"}}),
    ],
)
@pytest.mark.asyncio
async def test_set_state_payload_includes_result_and_error(
    result, error, expected_dynamic_fields
):

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload == {
            "reviewId": "review-1",
            "status": "finished",
            **expected_dynamic_fields,
        }
        return httpx.Response(
            200, request=request, json={"review": {"status": "finished"}}
        )

    async def fake_sleep(_: float) -> None:
        pass

    async with ReviewStateClient(
        "https://example.test",
        "token",
        transport=httpx.MockTransport(handler),
        sleep=fake_sleep,
    ) as client:
        _ = await client.set_state(
            "review-1",
            "finished",
            result=result,
            error=error,
        )


@pytest.mark.asyncio
async def test_set_state_raises_on_invalid_status_returned():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, request=request, json={"review": {"status": "BAD"}})

    async def fake_sleep(_: float) -> None:
        pass

    with pytest.raises(ReviewStateError, match="invalid review status"):
        async with ReviewStateClient(
            "https://example.test",
            "token",
            transport=httpx.MockTransport(handler),
            sleep=fake_sleep,
        ) as client:
            _ = await client.set_state("review-1", "finished")


@pytest.mark.asyncio
async def test_set_state_raises_on_invalid_response_shape():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, request=request, json={"BAD-KEY": {"WRONG": "BAD-VAL"}}
        )

    async def fake_sleep(_: float) -> None:
        pass

    with pytest.raises(ReviewStateError, match="Could not persist review state"):
        async with ReviewStateClient(
            "https://example.test",
            "token",
            transport=httpx.MockTransport(handler),
            sleep=fake_sleep,
        ) as client:
            _ = await client.set_state("review-1", "finished")
