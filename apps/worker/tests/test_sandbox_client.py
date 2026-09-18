import httpx
import pytest
from src.sandbox_client import SandboxClient


@pytest.mark.asyncio
async def test_exec_sends_expected_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/sandboxes/sandbox-1/exec"
        assert request.headers["X-Sandbox-Controller-Token"] == "secret"
        assert request.content == (
            b'{"command":["python","main.py"],"cwd":"/workspace/repo","env":{},"timeout_seconds":30}'
        )
        return httpx.Response(
            200,
            request=request,
            json={"exit_code": 0},
        )

    async with SandboxClient(
        base_url="https://sandbox.test",
        timeout_seconds=30,
        token="secret",
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await client.exec(
            "sandbox-1",
            ["python", "main.py"],
        )

    assert result == {"exit_code": 0}


@pytest.mark.asyncio
async def test_destroy_ignores_404() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, request=request)

    async with SandboxClient(
        base_url="https://sandbox.test",
        timeout_seconds=30,
        token="secret",
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await client.destroy("sandbox-1")

    assert result is None


@pytest.mark.parametrize("status_code", [400, 503])
@pytest.mark.asyncio
async def test_destroy_raises_for_other_errors(status_code: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, request=request)

    with pytest.raises(httpx.HTTPStatusError):
        async with SandboxClient(
            base_url="https://sandbox.test",
            timeout_seconds=30,
            token="secret",
            transport=httpx.MockTransport(handler),
        ) as client:
            await client.destroy("sandbox-1")
