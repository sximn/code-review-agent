"""Execution sessions checkpoint their output before bounded cleanup."""

import asyncio
import base64
import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

import httpx

from .agent.agent import run_agent_review, run_mock_agent_review
from .agent.pricing import estimate_review_cost, mock_review_cost
from .agent.schema import PRMetadata, ReviewCost, ReviewUsage
from .agent.usage import UsageAccumulator
from .completion import ReviewCompletion
from .config import AppConfig
from .repository import ReviewRequestPayload, fetch_pr_metadata, uriEncode
from .sandbox_client import SandboxClient

logger = logging.getLogger(__name__)


def _git_environment(github_token: str | None) -> dict[str, str]:
    environment = {"GIT_TERMINAL_PROMPT": "0"}
    if not github_token:
        return environment
    credentials = base64.b64encode(f"x-access-token:{github_token}".encode()).decode()
    environment.update(
        {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
            "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {credentials}",
        }
    )
    return environment


def _command_error(label: str, result: dict[str, Any]) -> RuntimeError:
    stderr = str(result.get("stderr", ""))[:2000]
    return RuntimeError(f"{label} failed: {stderr or 'unknown command error'}")


async def _require_command(
    sandbox: SandboxClient,
    sandbox_id: str,
    command: list[str],
    cwd: str = "/workspace/repo",
    env: dict[str, str] | None = None,
    *,
    label: str,
) -> dict[str, Any]:
    result = await sandbox.exec(sandbox_id, command, cwd, env)
    if result.get("exit_code") != 0:
        raise _command_error(label, result)
    return result


class ReviewExecutor:
    def __init__(
        self,
        config: AppConfig,
        github_client: httpx.AsyncClient,
        sandbox_factory: Callable[[], SandboxClient],
    ) -> None:
        self.config = config
        self.github_client = github_client
        self.sandbox_factory = sandbox_factory

    @asynccontextmanager
    async def open(self, job_id: str) -> AsyncGenerator["ReviewSession"]:
        session = ReviewSession(
            self.config, self.github_client, self.sandbox_factory(), job_id
        )
        try:
            yield session
        finally:
            await session.cleanup()


class ReviewSession:
    def __init__(
        self,
        config: AppConfig,
        github_client: httpx.AsyncClient,
        sandbox_client: SandboxClient,
        job_id: str,
    ) -> None:
        self.config = config
        self.github_client = github_client
        self.sandbox_client = sandbox_client
        self.job_id = job_id
        self.sandbox_id: str | None = None

    async def run(self, payload: ReviewRequestPayload) -> ReviewCompletion:
        config = self.config
        job_id = self.job_id
        sandbox_client = self.sandbox_client
        repository_url = (
            f"https://github.com/{uriEncode(payload.repository_owner)}/"
            f"{uriEncode(payload.repository_name)}.git"
        )
        git_environment = _git_environment(config.github_token)
        sandbox_id: str | None = None
        result: dict[str, Any] | None = None
        failure: str | None = None
        usage_accumulator: UsageAccumulator | None = None
        usage: ReviewUsage | None = None
        cost: ReviewCost | None = None

        try:
            async with asyncio.timeout(config.job_timeout_seconds):
                metadata = await fetch_pr_metadata(
                    self.github_client, payload, config.github_token
                )
                sandbox_id = await sandbox_client.create(job_id)
                self.sandbox_id = sandbox_id
                await _require_command(
                    sandbox_client,
                    sandbox_id,
                    [
                        "git",
                        "clone",
                        "--filter=blob:none",
                        "--no-checkout",
                        repository_url,
                        "/workspace/repo",
                    ],
                    "/workspace",
                    git_environment,
                    label="Repository clone",
                )
                size = await _require_command(
                    sandbox_client,
                    sandbox_id,
                    ["du", "-sb", "/workspace/repo"],
                    "/workspace",
                    label="Repository size check",
                )
                try:
                    repo_size = int(str(size.get("stdout", "")).split()[0])
                except (IndexError, ValueError) as exc:
                    raise RuntimeError("Could not determine repository size.") from exc
                if repo_size > config.max_repo_size_bytes:
                    raise RuntimeError(
                        "Repository is too large after the partial clone."
                    )

                for label, revision in (
                    ("Pull request base fetch", metadata.base_sha),
                    ("Pull request head fetch", metadata.head_sha),
                ):
                    await _require_command(
                        sandbox_client,
                        sandbox_id,
                        ["git", "fetch", "--no-tags", "--depth=1", "origin", revision],
                        env=git_environment,
                        label=label,
                    )
                await _require_command(
                    sandbox_client,
                    sandbox_id,
                    ["git", "checkout", "--detach", metadata.head_sha],
                    label="Pull request checkout",
                )
                checkout_size = await _require_command(
                    sandbox_client,
                    sandbox_id,
                    ["du", "-sb", "/workspace/repo"],
                    "/workspace",
                    label="Checked-out repository size check",
                )
                try:
                    repo_size = int(str(checkout_size.get("stdout", "")).split()[0])
                except (IndexError, ValueError) as exc:
                    raise RuntimeError("Could not determine checkout size.") from exc
                if repo_size > config.max_repo_size_bytes:
                    raise RuntimeError("Checked-out repository is too large.")

                pr_metadata = PRMetadata(
                    title=metadata.title,
                    description=metadata.description,
                    diff=metadata.diff,
                )
                if config.agent_mode == "mock":
                    review = await run_mock_agent_review(pr_metadata)
                    cost = mock_review_cost()
                else:
                    if not config.openai_api_key:
                        raise RuntimeError("OPENAI_API_KEY is missing.")
                    usage_accumulator = UsageAccumulator()
                    review = await run_agent_review(
                        pr_metadata,
                        config.model,
                        config.openai_api_key,
                        config.max_steps,
                        sandbox=sandbox_client,
                        sandbox_id=sandbox_id,
                        usage_accumulator=usage_accumulator,
                    )
                result = review.model_dump(mode="json")
        except TimeoutError:
            failure = (
                f"The review exceeded the {config.job_timeout_seconds}-second deadline."
            )
            logger.exception("Review %s timed out", job_id)
        except Exception as exc:
            failure = (str(exc) or type(exc).__name__)[:2000]
            logger.exception("Review %s failed", job_id)
        if usage_accumulator is not None:
            usage = usage_accumulator.materialize()
            cost = estimate_review_cost(
                usage, run_completed=(failure is None and result is not None)
            )
        usage_payload = usage.model_dump(mode="json") if usage is not None else None
        cost_payload = cost.model_dump(mode="json") if cost is not None else None
        if failure is not None:
            return ReviewCompletion(
                status="failed", error=failure, usage=usage_payload, cost=cost_payload
            )
        if result is None:
            raise RuntimeError("Review completed without a result.")
        return ReviewCompletion(
            status="finished", result=result, usage=usage_payload, cost=cost_payload
        )

    async def cleanup(self) -> None:
        # Optional new setting, with a finite fallback for existing AppConfig.
        seconds = getattr(self.config, "sandbox_cleanup_timeout_seconds", 10.0)
        if seconds <= 0:
            seconds = 10.0
        if self.sandbox_id is not None:
            try:
                async with asyncio.timeout(seconds):
                    await self.sandbox_client.destroy(self.sandbox_id)
            except Exception:
                logger.exception("Failed to destroy sandbox %s", self.sandbox_id)
        try:
            async with asyncio.timeout(seconds):
                await self.sandbox_client.close()
        except Exception:
            logger.exception("Failed to close sandbox client")
