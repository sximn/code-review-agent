from typing import Annotated
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from src.config import SandboxConfig
from src.sandbox_manager import ExecOutput, SandboxManager


def test_health(
    client: TestClient, mock_manager: Annotated[MagicMock, SandboxManager]
) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    mock_manager.client.ping.assert_called_once_with()


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-Sandbox-Controller-Token": "wrong-token"},
    ],
)
def test_protected_routes_require_token(
    client: TestClient, headers: dict[str, str]
) -> None:
    response = client.post(
        "/sandboxes",
        headers=headers,
        json={"job_id": "job-1"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


def test_create_sandbox(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    mock_manager: SandboxManager,
) -> None:
    create = MagicMock(return_value="container-123")
    monkeypatch.setattr(mock_manager, "create", create)

    response = client.post(
        "/sandboxes",
        headers=auth_headers,
        json={"job_id": "job-1"},
    )

    assert response.status_code == 200
    assert response.json() == {"id": "container-123"}
    create.assert_called_once_with("job-1")


def test_execute_command(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    mock_manager: SandboxManager,
) -> None:
    execute = MagicMock(
        return_value=ExecOutput(
            exit_code=0,
            stdout="hello\n",
            stderr="",
            truncated=False,
        )
    )
    monkeypatch.setattr(mock_manager, "execute", execute)

    response = client.post(
        "/sandboxes/container-123/exec",
        headers=auth_headers,
        json={
            "command": ["printf", "hello\n"],
            "cwd": "/workspace/repo",
            "env": {"EXAMPLE": "value"},
            "timeout_seconds": 10,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "exit_code": 0,
        "stdout": "hello\n",
        "stderr": "",
        "truncated": False,
    }
    execute.assert_called_once_with(
        "container-123",
        ["printf", "hello\n"],
        "/workspace/repo",
        {"EXAMPLE": "value"},
        10,
    )


def test_execute_caps_timeout_at_configured_maximum(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    mock_manager: SandboxManager,
    test_config: SandboxConfig,
) -> None:
    monkeypatch.setattr(test_config, "sandbox_command_timeout_seconds", 20)

    execute = MagicMock(
        return_value=ExecOutput(
            exit_code=0,
            stdout="",
            stderr="",
            truncated=False,
        )
    )
    monkeypatch.setattr(mock_manager, "execute", execute)

    response = client.post(
        "/sandboxes/container-123/exec",
        headers=auth_headers,
        json={
            "command": ["true"],
            "timeout_seconds": 40,
        },
    )

    assert response.status_code == 200
    assert execute.call_args.args[-1] == 20


def test_execute_unknown_sandbox_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    mock_manager: MagicMock,
) -> None:
    monkeypatch.setattr(
        mock_manager,
        "execute",
        MagicMock(side_effect=KeyError("missing")),
    )

    response = client.post(
        "/sandboxes/missing/exec",
        headers=auth_headers,
        json={"command": ["true"]},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Sandbox not found"}


def test_sandbox_status(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    mock_manager: MagicMock,
) -> None:
    container = MagicMock()
    container.id = "container-123"
    container.status = "running"
    monkeypatch.setattr(mock_manager, "get", MagicMock(return_value=container))

    response = client.get(
        "/sandboxes/container-123",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "container-123",
        "status": "running",
    }
    container.reload.assert_called_once_with()


def test_destroy_is_idempotent(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    mock_manager: MagicMock,
) -> None:
    destroy = MagicMock()
    monkeypatch.setattr(mock_manager, "destroy", destroy)

    response = client.delete(
        "/sandboxes/container-123",
        headers=auth_headers,
    )

    assert response.status_code == 204
    assert response.content == b""
    destroy.assert_called_once_with("container-123")
