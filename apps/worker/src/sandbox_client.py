from dataclasses import dataclass, field
from typing import Any, Self

import httpx


@dataclass
class SandboxClient:
    base_url: str
    timeout_seconds: int
    token: str
    _client: httpx.AsyncClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout_seconds + 15,
        )

    @property
    def headers(self) -> dict[str, str]:
        return {"X-Sandbox-Controller-Token": self.token}

    async def create(self, job_id: str) -> str:
        response = await self._client.post(
            "/sandboxes", json={"job_id": job_id}, headers=self.headers, timeout=20
        )
        response.raise_for_status()
        return response.json()["id"]

    async def exec(
        self,
        sandbox_id: str,
        command: list[str],
        cwd: str = "/workspace/repo",
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        response = await self._client.post(
            f"/sandboxes/{sandbox_id}/exec",
            json={
                "command": command,
                "cwd": cwd,
                "env": env or {},
                "timeout_seconds": self.timeout_seconds,
            },
            headers=self.headers,
        )
        response.raise_for_status()
        return response.json()

    async def destroy(self, sandbox_id: str) -> None:
        response = await self._client.delete(
            f"/sandboxes/{sandbox_id}", headers=self.headers, timeout=20
        )
        if response.status_code != 404:
            response.raise_for_status()

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()
