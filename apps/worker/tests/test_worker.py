import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from src import worker
from src.config import AppConfig
from src.processing_types import ProcessingOutcome, QueueMessage


@pytest.mark.asyncio
class TestWorker:
    @pytest.fixture
    def config(self, make_config) -> AppConfig:
        return make_config(
            job_stream="jobs",
            group_name="workers",
            worker_concurrency=2,
            job_reclaim_timeout_seconds=360,
        )

    @pytest.fixture
    def redis(self):
        client = Mock()
        client.xreadgroup = AsyncMock()
        client.xautoclaim = AsyncMock()
        client.xack = AsyncMock()
        return client

    @pytest.fixture
    def processor(self):
        processor = Mock()
        processor.process = AsyncMock(return_value=ProcessingOutcome.ACKNOWLEDGED)
        return processor

    async def test_new_messages_are_passed_to_processor(self, redis, config, processor):
        fields = {"job_id": "job-1"}
        redis.xreadgroup.return_value = [("jobs", [("123-0", fields)])]

        await worker.read_new_jobs(redis, config, processor, consumer_name="consumer-1")

        processor.process.assert_awaited_once_with(QueueMessage("123-0", fields))
        kwargs = redis.xreadgroup.await_args.kwargs
        assert kwargs["streams"] == {"jobs": ">"}
        assert kwargs["consumername"] == "consumer-1"
        redis.xack.assert_not_awaited()

    async def test_reclaim_follows_cursor_and_passes_messages(
        self, redis, config, processor
    ):
        fields = {"job_id": "job-1"}
        redis.xautoclaim.side_effect = [
            ("200-0", [("123-0", fields)], []),
            ("0-0", [], []),
        ]

        await worker.recover_stale_jobs(
            redis, config, processor, consumer_name="consumer-1"
        )

        assert redis.xautoclaim.await_count == 2
        calls = redis.xautoclaim.await_args_list
        assert calls[0].kwargs["start_id"] == "0-0"
        assert calls[1].kwargs["start_id"] == "200-0"
        assert calls[0].kwargs["consumername"] == "consumer-1"
        assert calls[0].kwargs["min_idle_time"] == 360000
        processor.process.assert_awaited_once_with(QueueMessage("123-0", fields))
        redis.xack.assert_not_awaited()

    async def test_one_unexpected_job_error_does_not_abandon_other_jobs(
        self, processor
    ):
        messages = [QueueMessage("1-0", {}), QueueMessage("2-0", {})]
        finished = []

        async def process(message):
            if message.message_id == "1-0":
                raise RuntimeError("bug")
            await asyncio.sleep(0.01)
            finished.append(message.message_id)
            return ProcessingOutcome.ACKNOWLEDGED

        processor.process.side_effect = process

        await worker.process_messages(processor, messages)

        assert processor.process.await_count == 2
        assert finished == ["2-0"]

    async def test_batch_cancellation_propagates(self, processor):
        processor.process.side_effect = asyncio.CancelledError()

        with pytest.raises(asyncio.CancelledError):
            await worker.process_messages(processor, [QueueMessage("1-0", {})])

    async def test_empty_read_does_not_process_or_ack(self, redis, config, processor):
        redis.xreadgroup.return_value = []

        await worker.read_new_jobs(redis, config, processor)

        processor.process.assert_not_awaited()
        redis.xack.assert_not_awaited()

    async def test_batch_cancellation_drains_sibling_tasks(self, processor):
        sibling_started = asyncio.Event()
        sibling_cleaned = asyncio.Event()

        async def process(message):
            if message.message_id == "1-0":
                await sibling_started.wait()
                raise asyncio.CancelledError()
            sibling_started.set()
            try:
                await asyncio.Event().wait()
            finally:
                sibling_cleaned.set()

        processor.process.side_effect = process

        with pytest.raises(asyncio.CancelledError):
            await worker.process_messages(
                processor, [QueueMessage("1-0", {}), QueueMessage("2-0", {})]
            )

        assert sibling_cleaned.is_set()
