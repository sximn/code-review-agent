import logging

from fastapi import Depends, FastAPI, Header, HTTPException

from .config import SandboxConfig
from .schemas import (
    CreateSandboxRequest,
    CreateSandboxResponse,
    ExecCommandRequest,
    ExecCommandResponse,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
config = SandboxConfig()  # pyright: ignore[reportCallIssue]


def require_token(
    x_sandbox_controller_token: str | None = Header(default=None),
) -> None:
    if x_sandbox_controller_token != config.sandbox_controller_token:
        raise HTTPException(status_code=401, detail="Unauthorized")


app = FastAPI()


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/sandboxes")
async def create_sandbox(
    request: CreateSandboxRequest, _: None = Depends(require_token)
) -> CreateSandboxResponse:
    try:
        logger.info("body: %s", str(request))
        # TODO:
        # sandbox_id = sb_manager.create()
        sandbox_id = "1"  # TODO: remove this after sandbox manager is implemented

        return CreateSandboxResponse(id=sandbox_id)
    except Exception as exc:
        logger.exception("Exception while creating a sandbox")
        raise HTTPException(
            status_code=500, detail="Failed to create a sandbox."
        ) from exc


@app.post("/sandboxes/{sandbox_id}/exec")
async def execute_command(
    sandbox_id: str, request: ExecCommandRequest, _: None = Depends(require_token)
) -> ExecCommandResponse:
    try:
        # TODO:
        # return await asyncio.to_thread(
        #     manager.exec, sandbox_id, request.command, request.cwd, request.env, request.timeout_seconds
        # )

        # TODO: removet his
        return ExecCommandResponse(
            exit_code=0, stdout="Hello from Sandbox", stderr="", truncated=False
        )
    except Exception as exc:
        logger.exception("Failed to execute a sandbox command")
        raise HTTPException(
            status_code=500, detail="Sandbox command execution failed."
        ) from exc


@app.delete("/sandboxes/{sandbox_id}")
async def destroy_sandbox(sandbox_id: str, _: None = Depends(require_token)) -> None:
    # TODO: sb_manager.destroy(sandbox_id)
    return
