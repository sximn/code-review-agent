import json
import logging
import os
import socket
import time
from typing import Any

from redis import Redis

from .config import AppConfig
from .pull_request import uriEncode

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CONSUMER_NAME = f"{socket.gethostname()}-{os.getpid()}"


def job_key(job_id: str) -> str:
    return f"repo-analyzer:job:{job_id}"


async def set_state(redis: Redis, job_id: str, status: str, **values: str) -> None:
    fields = {"status": status, **values}
    await redis.hset(job_key(job_id), mapping=fields)


def review_pull_request(
    job_id: str, payload: Any, redis: Redis, config: AppConfig
) -> None:
    repository, pr_number = (
        payload.get("repository", ""),
        payload.get("pull_request", ""),
    )

    owner, name = repository.split("/")
    if owner is None or name is None:
        raise RuntimeError("Received malformered repository handle.")

    repository_url = f"https://github.com/{uriEncode(owner)}/{uriEncode(name)}"

    if pr_number is None:
        raise RuntimeError("Missing pull request ID.")

    # TODO: create sandbox + checkout repo + start agent with PR metadata + tool calls -> structured output


def ensure_consumer_group(redis: Redis, config: AppConfig) -> None:
    try:
        redis.xgroup_create(
            name=config.job_stream,
            groupname=config.group_name,
            id="0",
            mkstream=True,
        )
        logger.info("Created consumer group %s", config.group_name)
    except redis.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise
        logger.info("Consumer group %s already exists", config.GROUP_NAME)


def recover_stale_jobs(redis: Redis, config: AppConfig) -> None:
    cursor = "0-0"

    while True:
        result = redis.xautoclaim(
            name=config.job_stream,
            groupname=config.group_name,
            consumername=CONSUMER_NAME,
            min_idle_time=config.job_reclaim_timeout_seconds,
            start_id=cursor,
            count=10,
        )

        # expecitng result to have shape:
        #
        # [
        #   next_cursor,
        #   [(message_id, fields), ...],
        #   [deleted_message_ids...],
        # ]
        cursor = result[0]
        messages = result[1]

        for message_id, fields in messages:
            logger.warning("Reclaimed stale job message_id=%s", message_id)

            process_message(message_id, fields)

        if cursor == "0-0":
            break


def process_job(fields: dict[str, str], redis: Redis, config: AppConfig) -> None:
    job_id = fields["job_id"]
    job_type = fields["type"]
    payload = json.loads(fields["payload"])

    logger.info(
        "Processing job_id=%s type=%s",
        job_id,
        job_type,
    )

    if job_type == config.review_job_name:
        review_pull_request(job_id, payload, redis, config)
    else:
        raise ValueError(f"Unknown job type: {job_type}")


def process_message(
    redis: Redis,
    config: AppConfig,
    message_id: str,
    fields: dict[str, str],
) -> None:
    try:
        process_job(fields, redis, config)

        acknowledged = redis.xack(
            config.job_stream,
            config.group_name,
            message_id,
        )

        logger.info(
            "Acknowledged message_id=%s result=%s",
            message_id,
            acknowledged,
        )

    except Exception:
        logger.exception(
            "Job failed; leaving it pending: message_id=%s",
            message_id,
        )
        # we do not send XACK here intentionally -> wait for it to be retrieved by XAUTOCLAIM


def read_new_jobs(redis: Redis, config: AppConfig) -> None:
    response = redis.xreadgroup(
        groupname=config.group_name,
        consumername=CONSUMER_NAME,
        streams={
            config.job_stream: ">",
        },
        count=10,
        block=5000,
    )

    if not response:
        return

    for stream_name, messages in response:
        for message_id, fields in messages:
            process_message(
                message_id,
                fields,
            )


def main() -> None:
    config = AppConfig()
    redis = Redis.from_url(config.redis_url, decode_responses=True)

    ensure_consumer_group(redis, config)
    logger.info(
        "Worker started stream=%s group=%s consumer=%s",
        config.job_stream,
        config.group_name,
        CONSUMER_NAME,
    )

    last_recovery = 0.0

    while True:
        try:
            now = time.monotonic()

            if now - last_recovery >= config.recovery_interval_seconds:
                recover_stale_jobs()
                last_recovery = now

            read_new_jobs()

        except redis.RedisError:
            logger.exception("Dragonfly error; retrying shortly")
            time.sleep(2)

        except Exception:
            logger.exception("Unexpected worker error")
            time.sleep(1)


if __name__ == "__main__":
    main()
