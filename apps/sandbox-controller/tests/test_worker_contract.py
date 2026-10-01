import asyncio
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock

import httpx
from src.config import SandboxConfig
from src.main import app, get_config, get_manager
from src.sandbox_manager import ExecOutput, SandboxManager


def load_worker_sandbox_client() -> type[Any]:
    module_path = Path(__file__).parents[2] / "worker" / "src" / "sandbox_client.py"
    spec = importlib.util.spec_from_file_location(
        "worker_sandbox_client_contract", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load worker client from {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert isinstance(module, ModuleType)
    return module.SandboxClient


def test_worker_client_matches_sandbox_controller_contract(
    test_config: SandboxConfig,
) -> None:
    manager = MagicMock(spec=SandboxManager)
    manager.create.return_value = "sandbox-123"
    manager.execute.return_value = ExecOutput(
        exit_code=0,
        stdout="hello\n",
        stderr="",
        truncated=False,
    )
    worker_client = load_worker_sandbox_client()

    app.dependency_overrides[get_config] = lambda: test_config
    app.dependency_overrides[get_manager] = lambda: manager

    async def exercise_boundary() -> None:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with worker_client(
            base_url="http://sandbox-controller.test",
            timeout_seconds=20,
            token=test_config.sandbox_controller_token,
            transport=transport,
        ) as client:
            sandbox_id = await client.create("job-1")
            result = await client.exec(sandbox_id, ["printf", "hello\\n"])
            await client.destroy(sandbox_id)

        assert sandbox_id == "sandbox-123"
        assert result == {
            "exit_code": 0,
            "stdout": "hello\n",
            "stderr": "",
            "truncated": False,
        }

    try:
        asyncio.run(exercise_boundary())
    finally:
        app.dependency_overrides.clear()

    manager.create.assert_called_once_with("job-1")
    manager.execute.assert_called_once_with(
        "sandbox-123",
        ["printf", "hello\\n"],
        "/workspace/repo",
        {},
        20,
    )
    manager.destroy.assert_called_once_with("sandbox-123")
