import asyncio
import uuid

import pytest
import pytest_asyncio
from redis import ResponseError
from redis.asyncio import Redis
from src.completion import ReviewCompletion
from src.completion_store import CompletionStore
from src.config import AppConfig
from src.processing_types import InvalidCheckpointError, QueueMessage, StorageError


@pytest.mark.asyncio
class TestCompletionStoreRedis:
    tag = "{tdd-" + uuid.uuid4().hex + "}"

    @pytest.fixture
    def redis(self, redis_async_client) -> Redis:
        return redis_async_client

    @pytest.fixture
    def config(self, make_config) -> AppConfig:
        return make_config(
            job_stream=f"{self.tag}:jobs",
            group_name="workers",
            completion_key_prefix=f"{self.tag}:completion",
            completion_dlq_stream=f"{self.tag}:dlq",
            completion_ttl_seconds=604800,
        )

    @pytest.fixture
    def key(self, config):
        return f"{config.completion_key_prefix}:job-1"

    @pytest.fixture
    def store(self, redis, config):
        return CompletionStore(redis=redis, config=config)

    @pytest.fixture
    def completion(self):
        return ReviewCompletion(
            status="finished",
            result={"summary": "OK"},
        )

    @pytest_asyncio.fixture(autouse=True)
    async def setup_store(self, redis, config, key):
        try:
            await redis.xgroup_create(
                config.job_stream,
                config.group_name,
                "0",
                mkstream=True,
            )
            fields = {
                "job_id": "job-1",
                "type": "review",
                "payload": "{}",
            }
            message_id = await redis.xadd(config.job_stream, fields)
            await redis.xreadgroup(
                config.group_name,
                "test-worker",
                {config.job_stream: ">"},
            )
            self.message = QueueMessage(message_id, fields)

            yield
        finally:
            # only delete keys this test created; never FLUSHDB
            await redis.delete(
                config.job_stream,
                config.completion_dlq_stream,
                key,
            )
            # redis_async_client fixture owns client cleanup

    async def pending_count(self, redis, config):
        return (
            await redis.xpending(
                config.job_stream,
                config.group_name,
            )
        )["pending"]

    async def test_group_created(self, redis, config):
        with pytest.raises(ResponseError, match="BUSYGROUP"):
            await redis.xgroup_create(
                config.job_stream,
                config.group_name,
                "0",
                mkstream=True,
            )

    async def test_round_trip_preserves_result_and_usage(self, store, completion):
        await store.save("job-1", completion)
        assert await store.load("job-1") == completion

    async def test_missing_checkpoint_returns_none(self, store):
        assert await store.load("missing") is None

    async def test_corrupt_checkpoint_raises_and_is_not_deleted(
        self, redis, store, key
    ):
        await redis.set(key, "broken")

        with pytest.raises(InvalidCheckpointError) as error:
            await store.load("job-1")

        assert error.value.raw_completion == "broken"
        assert await redis.get(key) == "broken"

    async def test_unresolved_checkpoint_has_no_expiry(
        self, redis, store, completion, key
    ):
        await store.save("job-1", completion)
        assert await redis.ttl(key) == -1

    async def test_record_failure_increments_without_changing_result(
        self, store, completion
    ):
        await store.save("job-1", completion)

        saved = await store.record_delivery_failure("job-1", "offline")

        assert saved.delivery_attempts == 1
        assert saved.last_delivery_error == "offline"
        assert saved.result == completion.result
        assert await store.load("job-1") == saved

    async def test_ack_removes_pending_message_and_checkpoint(
        self, redis, store, completion, config, key
    ):
        await redis.set(key, completion.model_dump_json())

        await store.acknowledge(self.message, job_id="job-1")

        assert await self.pending_count(redis=redis, config=config) == 0
        assert await redis.get(key) is None

    async def test_dlq_preserves_payload_and_finalizes_source(
        self, redis, store, completion, config, key
    ):
        await redis.set(key, completion.model_dump_json())

        await store.dead_letter(
            self.message,
            job_id="job-1",
            phase="delivery",
            reason="HTTP 422",
            completion=completion,
        )

        rows = await redis.xrange(config.completion_dlq_stream)
        assert rows is not None
        assert len(rows) == 1

        entry = rows[0][1]
        assert entry is not None
        assert entry["source_message_id"] == self.message.message_id
        assert entry["source_stream"] == config.job_stream
        assert entry["source_group"] == config.group_name
        assert entry["reason"] == "HTTP 422"
        assert ReviewCompletion.model_validate_json(entry["completion"]) == completion
        assert await self.pending_count(redis=redis, config=config) == 0
        assert await redis.get(key) is None

    async def test_repeated_dlq_call_does_not_duplicate_entry(
        self, redis, store, config, completion
    ):
        # Represents a retry when the first call's reply was lost.
        for _ in range(2):
            await store.dead_letter(
                self.message,
                job_id="job-1",
                phase="delivery",
                reason="rejected",
                completion=completion,
            )

        assert await redis.xlen(config.completion_dlq_stream) == 1
        assert await self.pending_count(redis=redis, config=config) == 0

    async def test_concurrent_dlq_calls_do_not_duplicate_entry(
        self, redis, store, completion, config
    ):
        await asyncio.gather(
            *(
                store.dead_letter(
                    self.message,
                    job_id="job-1",
                    phase="delivery",
                    reason="rejected",
                    completion=completion,
                )
                for _ in range(2)
            )
        )

        assert await redis.xlen(config.completion_dlq_stream) == 1
        assert await self.pending_count(redis=redis, config=config) == 0

    async def test_wrong_dlq_key_type_does_not_ack_or_delete_checkpoint(
        self, redis, store, completion, config, key
    ):
        await redis.set(key, completion.model_dump_json())
        await redis.set(config.completion_dlq_stream, "wrong-type")

        with pytest.raises(StorageError):
            await store.dead_letter(
                self.message,
                job_id="job-1",
                phase="delivery",
                reason="rejected",
                completion=completion,
            )

        assert await self.pending_count(redis=redis, config=config) == 1
        assert await redis.get(key) is not None
