import json

import httpx
import pytest
from src.review_state_client import (
    PermanentReviewStateError,
    ReviewStateClient,
    ReviewStateConfigurationError,
    ReviewStateProtocolError,
    TransientReviewStateError,
)


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


@pytest.mark.parametrize("status_code", [408, 425, 429, 503])
@pytest.mark.asyncio
async def test_set_state_classifies_exhausted_retryable_response_as_transient(
    status_code: int,
) -> None:
    attempts = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(status_code, request=request)

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)

    with pytest.raises(TransientReviewStateError, match="Could not persist"):
        async with ReviewStateClient(
            "https://example.test",
            "token",
            max_attempts=3,
            transport=httpx.MockTransport(handler),
            sleep=fake_sleep,
        ) as client:
            await client.set_state("review-1", "finished")

    assert attempts == 3
    assert delays == [0.5, 1.0]


@pytest.mark.asyncio
async def test_set_state_classifies_exhausted_transport_error_as_transient() -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ConnectError("offline")

    async def fake_sleep(_: float) -> None:
        pass

    with pytest.raises(TransientReviewStateError, match="Could not persist"):
        async with ReviewStateClient(
            "https://example.test",
            "token",
            max_attempts=2,
            transport=httpx.MockTransport(handler),
            sleep=fake_sleep,
        ) as client:
            await client.set_state("review-1", "finished")

    assert attempts == 2


@pytest.mark.parametrize("status_code", [400, 404, 409, 422])
@pytest.mark.asyncio
async def test_set_state_classifies_permanent_rejection_without_retry(
    status_code: int,
) -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(status_code, request=request)

    with pytest.raises(PermanentReviewStateError) as error:
        async with ReviewStateClient(
            "https://example.test",
            "token",
            transport=httpx.MockTransport(handler),
        ) as client:
            await client.set_state("review-1", "finished")

    assert error.value.status_code == status_code
    assert attempts == 1


@pytest.mark.parametrize("status_code", [401, 403])
@pytest.mark.asyncio
async def test_set_state_classifies_authentication_failure_as_configuration_error(
    status_code: int,
) -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(status_code, request=request)

    with pytest.raises(ReviewStateConfigurationError) as error:
        async with ReviewStateClient(
            "https://example.test",
            "token",
            transport=httpx.MockTransport(handler),
        ) as client:
            await client.set_state("review-1", "running")

    assert error.value.status_code == status_code
    assert attempts == 1


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
        assert request.url.path == "/api/v1/internal/reviews/review-1/state"
        assert payload == {
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
@pytest.mark.parametrize("invalid_status", ["BAD", ["finished"]])
async def test_set_state_raises_on_invalid_status_returned(invalid_status):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, request=request, json={"review": {"status": invalid_status}}
        )

    async def fake_sleep(_: float) -> None:
        pass

    with pytest.raises(ReviewStateProtocolError, match="invalid review status"):
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

    with pytest.raises(ReviewStateProtocolError, match="invalid review state response"):
        async with ReviewStateClient(
            "https://example.test",
            "token",
            transport=httpx.MockTransport(handler),
            sleep=fake_sleep,
        ) as client:
            _ = await client.set_state("review-1", "finished")
