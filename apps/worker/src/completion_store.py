import json
from datetime import UTC, datetime
from typing import Literal

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError, WatchError

from .completion import ReviewCompletion
from .config import AppConfig
from .processing_types import InvalidCheckpointError, QueueMessage, StorageError

# Declare every key to EVAL; keys must share a hash slot in Redis Cluster.
# Validate expected errors before the first write. No rollback is assumed.
# The pending entry is the idempotency guard: retries after ACK are no-ops.
_FINALIZE = """
local stream = KEYS[1]
local dlq = KEYS[2]
local checkpoint = KEYS[3]
local group = ARGV[1]
local message_id = ARGV[2]
local mode = ARGV[3]
local has_checkpoint = ARGV[4] == '1'

local function key_type(key)
    return redis.call('TYPE', key).ok
end

if key_type(stream) ~= 'stream' then
    return redis.error_reply('ERR Source stream is missing or has the wrong type')
end
-- Also verifies that the consumer group exists before any writes.
local pending = redis.call('XPENDING', stream, group, message_id, message_id, 1)
if #pending == 0 then
    return 0
end
if mode ~= 'ack' and mode ~= 'dlq' then
    return redis.error_reply('ERR Unknown finalization mode')
end
if has_checkpoint then
    local kind = key_type(checkpoint)
    if kind ~= 'none' and kind ~= 'string' then
        return redis.error_reply('ERR Checkpoint has the wrong type')
    end
end
if mode == 'dlq' then
    local kind = key_type(dlq)
    if kind ~= 'none' and kind ~= 'stream' then
        return redis.error_reply('ERR DLQ has the wrong type')
    end
    if #ARGV < 6 or (#ARGV - 4) % 2 ~= 0 then
        return redis.error_reply('ERR Invalid DLQ fields')
    end
    redis.call('XADD', dlq, '*', unpack(ARGV, 5))
end
local acknowledged = redis.call('XACK', stream, group, message_id)
if acknowledged == 1 and has_checkpoint then
    redis.call('DEL', checkpoint)
end
return acknowledged
"""


class CompletionStore:
    def __init__(self, redis: Redis, config: AppConfig) -> None:
        self.redis = redis
        self.config = config

    def _key(self, job_id: str) -> str:
        return f"{self.config.completion_key_prefix}:{job_id}"

    @staticmethod
    def _decode(raw: str | bytes) -> ReviewCompletion:
        try:
            return ReviewCompletion.model_validate_json(raw)
        except ValidationError as exc:
            text = (
                raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            )
            raise InvalidCheckpointError(text) from exc

    async def load(self, job_id: str) -> ReviewCompletion | None:
        try:
            raw = await self.redis.get(self._key(job_id))
        except RedisError as exc:
            raise StorageError(f"Could not load checkpoint for {job_id}") from exc
        return None if raw is None else self._decode(raw)

    async def save(self, job_id: str, completion: ReviewCompletion) -> None:
        try:
            # active deliveries must not expire -> SET also removes any old TTL
            await self.redis.set(self._key(job_id), completion.model_dump_json())
        except RedisError as exc:
            raise StorageError(f"Could not save checkpoint for {job_id}") from exc

    async def record_delivery_failure(
        self, job_id: str, reason: str
    ) -> ReviewCompletion:
        key = self._key(job_id)
        # WATCH preserves JSON/Pydantic serialization, including nested arrays,
        # while preventing lost concurrent attempt increments.
        for _ in range(16):
            try:
                async with self.redis.pipeline(transaction=True) as pipe:
                    await pipe.watch(key)
                    raw = await pipe.get(key)
                    if raw is None:
                        raise StorageError(f"Checkpoint for {job_id} disappeared")
                    completion = self._decode(raw)
                    completion.delivery_attempts += 1
                    completion.last_delivery_error = reason[:2000]
                    pipe.multi()
                    pipe.set(key, completion.model_dump_json())
                    await pipe.execute()
                    return completion
            except WatchError:
                continue
            except RedisError as exc:
                raise StorageError(
                    f"Could not record delivery failure for {job_id}"
                ) from exc
        raise StorageError(f"Checkpoint for {job_id} changed too often")

    async def _finalize(
        self,
        message: QueueMessage,
        job_id: str | None,
        mode: Literal["ack", "dlq"],
        entry: dict[str, str] | None = None,
    ) -> None:
        stream = self.config.job_stream
        # existing declared key is used as a placeholder for no checkpoint
        checkpoint = self._key(job_id) if job_id is not None else stream
        args: list[str] = [
            self.config.group_name,
            message.message_id,
            mode,
            "1" if job_id is not None else "0",
        ]
        if entry is not None:
            for name, value in entry.items():
                args.extend((name, value))
        try:
            await self.redis.eval(
                _FINALIZE,
                3,
                stream,
                self.config.completion_dlq_stream,
                checkpoint,
                *args,
            )
        except RedisError as exc:
            raise StorageError(
                f"Could not finalize message {message.message_id}"
            ) from exc

    async def acknowledge(self, message: QueueMessage, *, job_id: str | None) -> None:
        await self._finalize(message, job_id, "ack")

    async def dead_letter(
        self,
        message: QueueMessage,
        *,
        job_id: str | None,
        phase: str,
        reason: str,
        completion: ReviewCompletion | None = None,
        raw_completion: str | None = None,
    ) -> None:
        entry = {
            "source_message_id": message.message_id,
            "source_stream": self.config.job_stream,
            "source_group": self.config.group_name,
            "phase": phase,
            "reason": reason[:2000],
            "failed_at": datetime.now(UTC).isoformat(),
            "job": json.dumps(message.fields, sort_keys=True),
        }
        if job_id is not None:
            entry["job_id"] = job_id
        if completion is not None:
            entry["completion"] = completion.model_dump_json()
        if raw_completion is not None:
            entry["raw_completion"] = raw_completion[:10000]
        await self._finalize(message, job_id, "dlq", entry)
