from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class SandboxClient:
    base_url: str
    timeout_seconds: int
    token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"X-Sandbox-Controller-Token": self.token}

    async def create(self, job_id: str) -> str:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=20) as client:
            response = await client.post(
                "/sandboxes", json={"job_id": job_id}, headers=self.headers
            )
            response.raise_for_status()
            return response.json()["id"]

    async def exec(
        self, sandbox_id: str, command: list[str], cwd: str = "/workspace/repo"
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self.base_url, timeout=self.timeout_seconds + 15
        ) as client:
            response = await client.post(
                f"/sandboxes/{sandbox_id}/exec",
                json={
                    "command": command,
                    "cwd": cwd,
                    "timeout_seconds": self.timeout_seconds,
                },
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def destroy(self, sandbox_id: str) -> None:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=20) as client:
            response = await client.delete(
                f"/sandboxes/{sandbox_id}", headers=self.headers
            )
            if response.status_code != 404:
                response.raise_for_status()
