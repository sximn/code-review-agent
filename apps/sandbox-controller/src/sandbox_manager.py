import threading
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
        self._create_lock = threading.Lock()

    def _labels(self, job_id: str) -> dict[str, str]:
        prefix = self.config.sandbox_label_prefix
        return {
            f"{prefix}.sandbox": "true",
            f"{prefix}.job-id": job_id,
            f"{prefix}.created-at": datetime.now(UTC).isoformat(),
        }

    def _ensure_sandbox_network(self) -> None:
        """Create network for the dynamically created containers

        These sandboxes are not part of the docker compose services
        and are created dynamically. We want them on a separate network.
        """
        try:
            self.client.networks.get(self.config.sandbox_network)
        except NotFound:
            self.client.networks.create(
                self.config.sandbox_network, driver="bridge", check_duplicate=True
            )

    def create(self, job_id: str) -> str:
        with self._create_lock:
            self._ensure_sandbox_network()

            active = self.client.containers.list(
                all=True,
                filters={"label": f"{self.config.sandbox_label_prefix}.sandbox=true"},
            )

            # container creation and startup are two separate actions.
            # if a startup fails, created containers may be kept (in a state like "created", "exited", ...)
            # we remove these stale contaienrs to not count for the concurrency limit
            active_copy = active[:]
            # loop over copy to allow us to remove items from the active list
            for sandbox in active_copy:
                sandbox.reload()
                if sandbox.status != "running":
                    sandbox.remove(force=True)
                    active.remove(sandbox)

            if len(active) >= self.config.sandbox_max_concurrent:
                raise RuntimeError("Maximum concurrent sandbox count reached.")

            container = self.client.containers.create(
                image=self.config.sandbox_image,
                name=f"{self.config.sandbox_label_prefix}-job-{job_id}",
                runtime=self.config.sandbox_runtime,
                command=["sleep", "infinity"],
                user="1000:1000",
                cap_drop=["ALL"],
                security_opt=["no-new-privileges:true"],
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
    ) -> ExecOutput:
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

        stdout_buffer: list[bytes] = []
        stderr_buffer: list[bytes] = []
        stdout_current_count = 0
        stderr_current_count = 0
        stdout_truncated = False
        stderr_truncated = False
        for stdout, stderr in stream:
            if stdout:
                remaining = MAX_STDOUT_BYTES - stdout_current_count
                stdout_to_append = stdout[: max(remaining, 0)]
                if stdout_to_append:
                    stdout_buffer.append(stdout_to_append)
                    stdout_current_count += len(stdout_to_append)

                if len(stdout) > remaining:
                    stdout_truncated = True

            if stderr:
                remaining = MAX_STDERR_BYTES - stderr_current_count
                stderr_to_append = stderr[: max(remaining, 0)]
                if stderr_to_append:
                    stderr_buffer.append(stderr_to_append)
                    stderr_current_count += len(stderr_to_append)

                if len(stderr) > remaining:
                    stderr_truncated = True

        code = self.client.api.exec_inspect(exec_id)["ExitCode"]
        stdout = b"".join(stdout_buffer).decode("utf-8", errors="replace")
        stderr = b"".join(stderr_buffer).decode("utf-8", errors="replace")

        if stdout_truncated:
            stdout += "\n[output truncated]"
        if stderr_truncated:
            stderr += "\n[output truncated]"

        return ExecOutput(
            exit_code=code,
            stdout=stdout,
            stderr=stderr,
            truncated=stdout_truncated or stderr_truncated,
        )

    def destroy(self, sandbox_id: str) -> None:
        try:
            container = self.get(sandbox_id)
        except KeyError:
            return
        container.remove(force=True)

    def close(self):
        self.client.close()
