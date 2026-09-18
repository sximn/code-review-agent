import asyncio
import base64
import json
import logging
import os
import socket
from typing import Any, TypeAlias, cast

import httpx
from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError, ResponseError

from .agent import PRMetadata, run_agent_review, run_mock_agent_review
from .config import AppConfig
from .repository import (
    ReviewRequestPayload,
    fetch_pr_metadata,
    uriEncode,
)
from .review_state_client import ReviewStateClient
from .sandbox_client import SandboxClient

StreamMessage: TypeAlias = tuple[str, dict[str, str]]
StreamBatch: TypeAlias = tuple[str, list[StreamMessage]]
XReadGroupResponse: TypeAlias = list[StreamBatch]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CONSUMER_NAME = f"{socket.gethostname()}-{os.getpid()}"


class InvalidJobError(ValueError):
    pass


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


async def review_pull_request(
    job_id: str,
    payload: ReviewRequestPayload,
    config: AppConfig,
    sandbox_client: SandboxClient,
    state_client: ReviewStateClient,
    github_client: httpx.AsyncClient,
) -> None:
    repository_url = f"https://github.com/{uriEncode(payload.repository_owner)}/{uriEncode(payload.repository_name)}.git"
    git_environment = _git_environment(config.github_token)
    sandbox_id: str | None = None
    result: dict[str, Any] | None = None
    failure: str | None = None

    current_status = await state_client.set_state(job_id, "running")
    if current_status in {"failed", "finished"}:
        logger.info(
            "Review %s is already terminal with status=%s",
            job_id,
            current_status,
        )
        return

    try:
        async with asyncio.timeout(config.job_timeout_seconds):
            metadata = await fetch_pr_metadata(
                github_client,
                payload,
                config.github_token,
            )

            sandbox_id = await sandbox_client.create(job_id)

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
                raise RuntimeError("Repository is too large after the partial clone.")

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
            else:
                if not config.openai_api_key:
                    raise RuntimeError("OPENAI_API_KEY is missing.")
                review = await run_agent_review(
                    pr_metadata,
                    config.model,
                    config.openai_api_key,
                    config.max_steps,
                    sandbox_client,
                    sandbox_id,
                )

            result = review.model_dump(mode="json")
    except TimeoutError:
        failure = (
            f"The review exceeded the {config.job_timeout_seconds}-second deadline."
        )
        logger.exception("Review %s timed out", job_id)
    except Exception as exc:
        failure = str(exc)[:2000]
        logger.exception("Review %s failed", job_id)
    finally:
        if sandbox_id:
            try:
                await sandbox_client.destroy(sandbox_id)
            except Exception:
                logger.exception("Failed to destroy sandbox %s", sandbox_id)
        await sandbox_client.close()

    if failure is not None:
        await state_client.set_state(
            job_id,
            "failed",
            error=failure,
        )
        return

    if result is None:
        raise RuntimeError("Review completed without a result.")
    await state_client.set_state(
        job_id,
        "finished",
        result=result,
    )


async def ensure_consumer_group(redis: Redis, config: AppConfig) -> None:
    try:
        await redis.xgroup_create(
            name=config.job_stream,
            groupname=config.group_name,
            id="0",
            mkstream=True,
        )
        logger.info("Created consumer group %s", config.group_name)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise
        logger.info("Consumer group %s already exists", config.group_name)


async def process_job(
    fields: dict[str, str],
    config: AppConfig,
    state_client: ReviewStateClient,
    github_client: httpx.AsyncClient,
) -> None:
    try:
        job_id = fields["job_id"]
        job_type = fields["type"]
        raw_payload = json.loads(fields["payload"])
    except (KeyError, json.JSONDecodeError) as exc:
        raise InvalidJobError(
            "Job message is missing required fields or JSON."
        ) from exc

    logger.info("Processing job_id=%s type=%s", job_id, job_type)

    if job_type != config.review_job_name:
        raise InvalidJobError(f"Unknown job type: {job_type}")
    if not isinstance(raw_payload, dict):
        raise InvalidJobError("Job payload must be a JSON object.")

    try:
        payload = ReviewRequestPayload.model_validate(raw_payload)
    except ValidationError:
        await state_client.set_state(
            job_id,
            "failed",
            error="The queued review payload is invalid.",
        )
        return

    sandbox = SandboxClient(
        config.sandbox_controller_url,
        config.command_timeout_seconds,
        config.sandbox_controller_token,
    )
    await review_pull_request(
        job_id, payload, config, sandbox, state_client, github_client
    )


async def process_message(
    redis: Redis,
    config: AppConfig,
    state_client: ReviewStateClient,
    github_client: httpx.AsyncClient,
    message_id: str,
    fields: dict[str, str],
) -> None:
    try:
        await process_job(fields, config, state_client, github_client)
        acknowledged = await redis.xack(
            config.job_stream,
            config.group_name,
            message_id,
        )
        logger.info(
            "Acknowledged message_id=%s result=%s",
            message_id,
            acknowledged,
        )
    except InvalidJobError:
        logger.exception("Discarding invalid job message_id=%s", message_id)
        await redis.xack(config.job_stream, config.group_name, message_id)
    except Exception:
        logger.exception(
            "Job could not reach a terminal state; leaving it pending: message_id=%s",
            message_id,
        )


async def _process_messages(
    redis: Redis,
    config: AppConfig,
    state_client: ReviewStateClient,
    github_client: httpx.AsyncClient,
    messages: list[tuple[str, dict[str, str]]],
) -> None:
    await asyncio.gather(
        *(
            process_message(
                redis, config, state_client, github_client, message_id, fields
            )
            for message_id, fields in messages
        )
    )


async def recover_stale_jobs(
    redis: Redis,
    config: AppConfig,
    state_client: ReviewStateClient,
    github_client: httpx.AsyncClient,
) -> None:
    cursor = "0-0"

    while True:
        result = await redis.xautoclaim(
            name=config.job_stream,
            groupname=config.group_name,
            consumername=CONSUMER_NAME,
            min_idle_time=config.job_reclaim_timeout_seconds * 1000,
            start_id=cursor,
            count=config.worker_concurrency,
        )
        cursor = result[0]
        messages = result[1]

        for message_id, _ in messages:
            logger.warning("Reclaimed stale job message_id=%s", message_id)
        if messages:
            await _process_messages(
                redis, config, state_client, github_client, messages
            )

        if cursor == "0-0":
            break


async def read_new_jobs(
    redis: Redis,
    config: AppConfig,
    state_client: ReviewStateClient,
    github_client: httpx.AsyncClient,
) -> None:
    raw_response = await redis.xreadgroup(
        groupname=config.group_name,
        consumername=CONSUMER_NAME,
        streams={config.job_stream: ">"},
        count=config.worker_concurrency,
        block=5000,
    )

    response = cast(XReadGroupResponse | None, raw_response)
    for _, messages in response or []:
        await _process_messages(redis, config, state_client, github_client, messages)


async def run_worker() -> None:
    config = AppConfig()  # pyright: ignore[reportCallIssue]
    redis = Redis.from_url(
        config.redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=15,
    )

    if config.job_reclaim_timeout_seconds <= config.job_timeout_seconds:
        logger.warning(
            "JOB_RECLAIM_TIMEOUT_SECONDS should exceed JOB_TIMEOUT_SECONDS to avoid "
            "reclaiming a review that is still running."
        )

    state_client = ReviewStateClient(
        config.web_service_url,
        config.worker_api_token,
    )

    try:
        async with (
            state_client,
            httpx.AsyncClient(timeout=30) as github_client,
        ):
            await ensure_consumer_group(redis, config)
            logger.info(
                "Worker started in %s mode | stream=%s group=%s consumer=%s concurrency=%s",
                config.agent_mode.upper(),
                config.job_stream,
                config.group_name,
                CONSUMER_NAME,
                config.worker_concurrency,
            )

            loop = asyncio.get_running_loop()
            last_recovery = 0.0

            while True:
                try:
                    now = loop.time()
                    if now - last_recovery >= config.recovery_interval_seconds:
                        await recover_stale_jobs(
                            redis, config, state_client, github_client
                        )
                        last_recovery = now

                    await read_new_jobs(redis, config, state_client, github_client)
                except RedisError:
                    logger.exception("Redis/Dragonfly error; retrying shortly")
                    await asyncio.sleep(2)
                except Exception:
                    logger.exception("Unexpected worker error")
                    await asyncio.sleep(1)
    finally:
        await redis.aclose()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
