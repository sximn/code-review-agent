import asyncio
from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_result_available_before_cleanup(review_execution) -> None:
    async with review_execution.executor.open("job-1") as session:
        completion = await session.run(review_execution.payload)

        assert completion.status == "finished"
        review_execution.sandbox.destroy.assert_not_awaited()
        review_execution.sandbox.close.assert_not_awaited()

    review_execution.sandbox.destroy.assert_awaited_once_with("sandbox-1")
    review_execution.sandbox.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_error_still_cleans_up_and_propagates(
    review_execution: SimpleNamespace,
) -> None:
    with pytest.raises(RuntimeError, match="save failed"):
        async with review_execution.executor.open("job-1") as session:
            await session.run(review_execution.payload)
            raise RuntimeError("save failed")

    review_execution.sandbox.destroy.assert_awaited_once()
    review_execution.sandbox.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_errors_do_not_replace_primary_error(
    review_execution: SimpleNamespace,
) -> None:
    review_execution.sandbox.destroy.side_effect = RuntimeError("destroy failed")
    review_execution.sandbox.close.side_effect = RuntimeError("close failed")

    with pytest.raises(RuntimeError, match="save failed"):
        async with review_execution.executor.open("job-1") as session:
            await session.run(review_execution.payload)
            raise RuntimeError("save failed")

    review_execution.sandbox.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_hung_destroy_is_bounded_and_client_close_is_attempted(
    review_execution: SimpleNamespace,
) -> None:
    async def hung(*args: object) -> None:
        await asyncio.Event().wait()

    review_execution.sandbox.destroy.side_effect = hung

    async with asyncio.timeout(1):
        async with review_execution.executor.open("job-1") as session:
            await session.run(review_execution.payload)

    review_execution.sandbox.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_execution_failure_returns_valid_failed_completion(
    review_execution: SimpleNamespace,
) -> None:
    review_execution.agent.side_effect = RuntimeError()

    async with review_execution.executor.open("job-1") as session:
        completion = await session.run(review_execution.payload)

        assert completion.status == "failed"
        assert completion.error == "RuntimeError"


@pytest.mark.asyncio
async def test_job_timeout_returns_failed_completion(
    review_execution: SimpleNamespace,
) -> None:
    review_execution.config.job_timeout_seconds = 0.02

    async def hung(*args: object) -> None:
        await asyncio.Event().wait()

    review_execution.metadata.side_effect = hung

    async with review_execution.executor.open("job-1") as session:
        completion = await session.run(review_execution.payload)

        assert completion.status == "failed"
        assert "deadline" in completion.error

    review_execution.sandbox.create.assert_not_awaited()
    review_execution.sandbox.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancellation_propagates_and_cleans_up(
    review_execution: SimpleNamespace,
) -> None:
    review_execution.agent.side_effect = asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        async with review_execution.executor.open("job-1") as session:
            await session.run(review_execution.payload)

    review_execution.sandbox.destroy.assert_awaited_once()
    review_execution.sandbox.close.assert_awaited_once()
