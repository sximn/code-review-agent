import asyncio
import logging
import secrets
from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Annotated

from docker.errors import DockerException
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.concurrency import asynccontextmanager

from .config import SandboxConfig
from .sandbox_manager import SandboxManager
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


app = FastAPI(lifespan=lifespan)

ConfigDependency = Annotated[SandboxConfig, Depends(get_config)]
ManagerDependency = Annotated[SandboxManager, Depends(get_manager)]


def require_token(
    config: ConfigDependency,
    token: Annotated[
        str | None,
        Header(alias="X-Sandbox-Controller-Token"),
    ] = None,
) -> None:
    if not secrets.compare_digest(token or "", config.sandbox_controller_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )


AuthDependency = Annotated[None, Depends(require_token)]


@app.get("/health")
async def health(manager: ManagerDependency) -> dict[str, bool]:
    await asyncio.to_thread(manager.client.ping)
    return {"ok": True}


@app.post("/sandboxes")
async def create_sandbox(
    request: CreateSandboxRequest,
    _: AuthDependency,
    manager: ManagerDependency,
) -> CreateSandboxResponse:
    try:
        sandbox_id = await asyncio.to_thread(manager.create, request.job_id)

        return CreateSandboxResponse(id=sandbox_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DockerException as exc:
        logger.exception("Docker failed to create a sandbox")
        raise HTTPException(
            status_code=503,
            detail="Sandbox runtime is unavailable.",
        ) from exc


@app.post("/sandboxes/{sandbox_id}/exec")
async def execute_command(
    sandbox_id: str,
    request: ExecCommandRequest,
    _: AuthDependency,
    config: ConfigDependency,
    manager: ManagerDependency,
) -> ExecCommandResponse:
    try:
        timeout = min(
            request.timeout_seconds or config.sandbox_command_timeout_seconds,
            config.sandbox_command_timeout_seconds,
        )
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
        raise HTTPException(status_code=404, detail="Sandbox not found") from exc
    except DockerException as exc:
        logger.exception("Docker failed to execute a sandbox command")
        raise HTTPException(
            status_code=503, detail="Sandbox command execution failed."
        ) from exc
    except Exception as exc:
        logger.exception("Failed to execute a sandbox command")
        raise HTTPException(
            status_code=500, detail="Sandbox command execution failed."
        ) from exc


@app.get("/sandboxes/{sandbox_id}")
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
        raise HTTPException(status_code=404, detail="Sandbox not found") from exc


@app.delete("/sandboxes/{sandbox_id}")
async def destroy_sandbox(
    sandbox_id: str,
    _: AuthDependency,
    manager: ManagerDependency,
) -> None:
    await asyncio.to_thread(manager.destroy, sandbox_id)
