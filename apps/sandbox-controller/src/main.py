import asyncio
import logging
import secrets
from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Annotated

from docker.errors import DockerException
from fastapi import Depends, FastAPI, HTTPException, Request, Response, Security, status
from fastapi.concurrency import asynccontextmanager
from fastapi.security import APIKeyHeader

from .config import SandboxConfig
from .sandbox_manager import SandboxCapacityError, SandboxManager
from .schemas import (
    CreateSandboxRequest,
    CreateSandboxResponse,
    ExecCommandRequest,
    ExecCommandResponse,
    SandboxStatusResponse,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@lru_cache
def get_config():
    return SandboxConfig()  # pyright: ignore[reportCallIssue]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    manager = SandboxManager(config=get_config())
    # fail app startup if Docker not available
    manager.client.ping()

    app.state.sandbox_manager = manager

    try:
        yield
    finally:
        manager.close()


def get_manager(request: Request) -> SandboxManager:
    return request.app.state.sandbox_manager


app = FastAPI(
    title="Sandbox Controller API",
    version="1.0.0",
    description="Internal API used by the review worker to manage sandboxes.",
    lifespan=lifespan,
)

ConfigDependency = Annotated[SandboxConfig, Depends(get_config)]
ManagerDependency = Annotated[SandboxManager, Depends(get_manager)]
token_header = APIKeyHeader(
    name="X-Sandbox-Controller-Token",
    scheme_name="sandboxControllerToken",
    auto_error=False,
)


def require_token(
    config: ConfigDependency,
    token: Annotated[str | None, Security(token_header)],
) -> None:
    if not secrets.compare_digest(token or "", config.sandbox_controller_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )


AuthDependency = Annotated[None, Depends(require_token)]


@app.get("/health", operation_id="health")
async def health(manager: ManagerDependency) -> dict[str, bool]:
    await asyncio.to_thread(manager.client.ping)
    return {"ok": True}


@app.post(
    "/sandboxes",
    operation_id="createSandbox",
    responses={
        401: {"description": "Unauthorized"},
        429: {"description": "Sandbox capacity exhausted"},
        503: {"description": "Sandbox runtime unavailable"},
    },
)
async def create_sandbox(
    request: CreateSandboxRequest,
    _: AuthDependency,
    manager: ManagerDependency,
) -> CreateSandboxResponse:
    try:
        sandbox_id = await asyncio.to_thread(manager.create, request.job_id)

        return CreateSandboxResponse(id=sandbox_id)

    except SandboxCapacityError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers={"Retry-After": "5"},
        ) from exc

    except DockerException as exc:
        logger.exception("Docker failed to create a sandbox")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sandbox runtime is unavailable.",
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected sandbox creation failure")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sandbox creation failed.",
        ) from exc


@app.post(
    "/sandboxes/{sandbox_id}/exec",
    operation_id="executeCommand",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Sandbox not found"},
        503: {"description": "Sandbox runtime unavailable"},
    },
)
async def execute_command(
    sandbox_id: str,
    request: ExecCommandRequest,
    _: AuthDependency,
    config: ConfigDependency,
    manager: ManagerDependency,
) -> ExecCommandResponse:
    requested_timeout = (
        request.timeout_seconds
        if request.timeout_seconds is not None
        else config.sandbox_command_timeout_seconds
    )
    timeout = min(requested_timeout, config.sandbox_command_timeout_seconds)

    try:
        exec_output = await asyncio.to_thread(
            manager.execute,
            sandbox_id,
            request.command,
            request.cwd,
            request.env,
            timeout,
        )
        return ExecCommandResponse(
            exit_code=exec_output.exit_code,
            stdout=exec_output.stdout,
            stderr=exec_output.stderr,
            truncated=exec_output.truncated,
        )

    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sandbox not found"
        ) from exc

    except DockerException as exc:
        logger.exception("Docker failed to execute a sandbox command")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sandbox command execution failed.",
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected failure during sandbox command execution")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sandbox command execution failed.",
        ) from exc


@app.get(
    "/sandboxes/{sandbox_id}",
    operation_id="getSandbox",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Sandbox not found"},
        503: {"description": "Sandbox runtime unavailable"},
    },
)
async def sandbox_status(
    sandbox_id: str,
    _: AuthDependency,
    manager: ManagerDependency,
) -> SandboxStatusResponse:
    try:
        container = await asyncio.to_thread(manager.get, sandbox_id)
        container.reload()
        return SandboxStatusResponse(
            id=container.id or "unknown", status=container.status
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sandbox not found"
        ) from exc

    except DockerException as exc:
        logger.exception("Docker failed to inspect a sandbox")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sandbox runtime is unavailable.",
        ) from exc


@app.delete(
    "/sandboxes/{sandbox_id}",
    operation_id="destroySandbox",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Unauthorized"},
        503: {"description": "Sandbox runtime unavailable"},
    },
)
async def destroy_sandbox(
    sandbox_id: str,
    _: AuthDependency,
    manager: ManagerDependency,
) -> Response:
    try:
        await asyncio.to_thread(manager.destroy, sandbox_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except DockerException as exc:
        logger.exception("Docker failed to destroy a sandbox")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sandbox destruction failed.",
        ) from exc
