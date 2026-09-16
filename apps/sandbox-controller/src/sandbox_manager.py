from datetime import UTC, datetime

import docker
from docker.errors import NotFound
from pydantic import BaseModel

from .config import SandboxConfig

MAX_STDOUT_BYTES = 50_000
MAX_STDERR_BYTES = 20_000


class ExecOutput(BaseModel):
    exit_code: int
    stdout: str
    stderr: str
    truncated: bool


class SandboxManager:
    def __init__(self, config: SandboxConfig):
        self.config = config
        self.client = docker.from_env()

    def _labels(self, job_id: str) -> dict[str, str]:
        prefix = self.config.sandbox_label_prefix
        return {
            f"{prefix}.sandbox": "true",
            f"{prefix}.job-id": job_id,
            f"{prefix}.created-at": datetime.now(UTC).isoformat(),
        }

    def create(self, job_id: str) -> str:

        container = self.client.containers.create(
            image=self.config.sandbox_image,
            name=f"{self.config.sandbox_label_prefix}-job-{job_id}",
            runtime=self.config.sandbox_runtime,
            command=["sleep", "infinity"],
            user="1000:1000",
            mem_limit=self.config.sandbox_memory,
            nano_cpus=int(self.config.sandbox_cpus * 1_000_000_000),
            pids_limit=self.config.sandbox_pids_limit,
            labels=self._labels(job_id),
            network=self.config.sandbox_network,
            tmpfs={"/tmp": "rw,noexec,nosuid,size=256m"},
            mounts=[],
        )
        try:
            container.start()
        except Exception:
            # attempt removal in case create succeeded
            container.remove(force=True)
            raise

        if container.id is None:
            raise ValueError("Malformed ID-less container")

        return container.id

    def get(self, sandbox_id: str):
        try:
            container = self.client.containers.get(sandbox_id)
        except NotFound as exc:
            raise KeyError(sandbox_id) from exc
        if (
            container.labels.get(f"{self.config.sandbox_label_prefix}.sandbox")
            != "true"
        ):
            raise KeyError(sandbox_id)
        return container

    def execute(
        self,
        sandbox_id: str,
        command: list[str],
        cwd: str,
        env: dict[str, str] | None,
        timeout_seconds: int,
    ):
        container = self.get(sandbox_id)

        wrapped = ["/usr/bin/timeout", "--signal=KILL", f"{timeout_seconds}s", *command]
        exec_id = self.client.api.exec_create(
            container.id,
            wrapped,
            workdir=cwd,
            environment=env,
            user="1000:1000",
            stdout=True,
            stderr=True,
        )["Id"]

        stream = self.client.api.exec_start(exec_id, stream=True, demux=True)

        stdout_buffer = []
        stdout_current_count = 0
        stderr_buffer = []
        stderr_current_count = 0
        truncated = False
        for stdout, stderr in stream:
            if stdout:
                remaining = MAX_STDOUT_BYTES - stdout_current_count
                stdout_to_append = stdout[: max(remaining, 0)]
                stdout_buffer.append(stdout_to_append)
                stdout_current_count += len(stdout_to_append)
                truncated: bool = truncated or len(stdout) > remaining
            if stderr:
                remaining = MAX_STDERR_BYTES - stderr_current_count
                stderr_to_append = stderr[: max(remaining, 0)]
                stderr_buffer.append(stderr_to_append)
                stderr_current_count += len(stderr_to_append)
                truncated = truncated or len(stderr) > remaining

        code = self.client.api.exec_inspect(exec_id)["ExitCode"]
        stdout = b"".join(stdout_buffer).decode("utf-8", errors="replace")
        stderr = b"".join(stderr_buffer).decode("utf-8", errors="replace")

        if truncated:
            stdout += "\n[output truncated]"

        return ExecOutput(
            exit_code=code,
            stdout=stdout,
            stderr=stderr,
            truncated=truncated,
        )

    def destroy(self, sandbox_id: str) -> None:
        try:
            container = self.get(sandbox_id)
        except KeyError:
            return
        container.remove(force=True)
