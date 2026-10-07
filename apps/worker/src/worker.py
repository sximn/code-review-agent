import asyncio
import logging
import os
import socket
from typing import TypeAlias, cast

import httpx
from redis.asyncio import Redis
from redis.exceptions import RedisError, ResponseError

from .completion_store import CompletionStore
from .config import AppConfig
from .job_processor import JobProcessor
from .processing_types import QueueMessage
from .review_execution import ReviewExecutor
from .review_state_client import ReviewStateClient
from .sandbox_client import SandboxClient

StreamMessage: TypeAlias = tuple[str, dict[str, str]]
StreamBatch: TypeAlias = tuple[str, list[StreamMessage]]
XReadGroupResponse: TypeAlias = list[StreamBatch]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CONSUMER_NAME = f"{socket.gethostname()}-{os.getpid()}"


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


async def process_messages(
    processor: JobProcessor, messages: list[QueueMessage]
) -> None:
    async def process_one(message: QueueMessage) -> None:
        try:
            await processor.process(message)
        except Exception:
            logger.exception(
                "Unexpected processing error; message remains pending: %s",
                message.message_id,
            )

    tasks = [asyncio.create_task(process_one(message)) for message in messages]
    try:
        await asyncio.gather(*tasks)
    except BaseException:
        # Drain the batch on cancellation too, so no work escapes this boundary.
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise


async def recover_stale_jobs(
    redis: Redis,
    config: AppConfig,
    processor: JobProcessor,
    *,
    consumer_name: str = CONSUMER_NAME,
) -> None:
    cursor = "0-0"

    while True:
        result = await redis.xautoclaim(
            name=config.job_stream,
            groupname=config.group_name,
            consumername=consumer_name,
            min_idle_time=config.job_reclaim_timeout_seconds * 1000,
            start_id=cursor,
            count=config.worker_concurrency,
        )
        cursor = result[0]
        messages = result[1]

        for message_id, _ in messages:
            logger.warning("Reclaimed stale job message_id=%s", message_id)
        if messages:
            await process_messages(
                processor,
                [QueueMessage(message_id, fields) for message_id, fields in messages],
            )
        if cursor == "0-0":
            break


async def read_new_jobs(
    redis: Redis,
    config: AppConfig,
    processor: JobProcessor,
    *,
    consumer_name: str = CONSUMER_NAME,
) -> None:
    raw_response = await redis.xreadgroup(
        groupname=config.group_name,
        consumername=consumer_name,
        streams={config.job_stream: ">"},
        count=config.worker_concurrency,
        block=5000,
    )

    response = cast(XReadGroupResponse | None, raw_response)
    for _, messages in response or []:
        await process_messages(
            processor,
            [QueueMessage(message_id, fields) for message_id, fields in messages],
        )


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
            store = CompletionStore(redis=redis, config=config)
            executor = ReviewExecutor(
                config=config,
                github_client=github_client,
                sandbox_factory=lambda: SandboxClient(
                    config.sandbox_controller_url,
                    config.command_timeout_seconds,
                    config.sandbox_controller_token,
                ),
            )
            processor = JobProcessor(
                config=config,
                store=store,
                executor=executor,
                state_client=state_client,
            )
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
                            redis,
                            config,
                            processor,
                        )
                        last_recovery = now

                    await read_new_jobs(redis, config, processor)
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
