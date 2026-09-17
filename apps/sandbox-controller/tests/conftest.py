from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
import src.main as main_module
from fastapi.testclient import TestClient
from src.config import SandboxConfig
from src.main import app, get_config
from src.sandbox_manager import SandboxManager


@pytest.fixture
def test_config() -> SandboxConfig:
    return SandboxConfig(
        sandbox_controller_token="test-token",
        sandbox_image="test-sandbox:latest",
        sandbox_runtime="runc",
        sandbox_memory="256m",
        sandbox_cpus=0.5,
        sandbox_pids_limit=64,
        sandbox_label_prefix="sandbox-test",
        sandbox_network="sandbox-test-network",
        sandbox_command_timeout_seconds=20,
        sandbox_max_lifetime_seconds=600,
        sandbox_max_concurrent=2,
    )


@pytest.fixture
def mock_manager() -> MagicMock:
    manager = MagicMock(spec=SandboxManager)
    manager.client = MagicMock()
    return manager


@pytest.fixture
def client(
    test_config: SandboxConfig,
    mock_manager: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    # Used by normal FastAPI dependency injection.
    app.dependency_overrides[get_config] = lambda: test_config

    # Used directly by lifespan(), which bypasses dependency_overrides.
    monkeypatch.setattr(main_module, "get_config", lambda: test_config)
    monkeypatch.setattr(
        main_module,
        "SandboxManager",
        lambda *, config: mock_manager,
    )

    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            # Discard calls made during startup, such as client.ping().
            mock_manager.reset_mock()
            yield test_client
    finally:
        app.dependency_overrides.clear()
        get_config.cache_clear()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"X-Sandbox-Controller-Token": "test-token"}
