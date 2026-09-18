import json
from typing import ClassVar
from unittest.mock import AsyncMock

import httpx
import pytest
from redis.asyncio import Redis
from src import worker
from src.review_state_client import ReviewStateClient
from src.sandbox_client import SandboxClient
from src.worker import InvalidJobError, _require_command, process_job, process_message
from tests.conftest import ConfigFactory


class TestHelperFunctions:
    @pytest.fixture
    def sandbox_client(self):
        return AsyncMock(SandboxClient)

    @pytest.mark.asyncio
    async def test_require_command_raises_on_stderr(self, sandbox_client):
        sandbox_client.exec = AsyncMock(
            return_value={"exit_code": 127, "stderr": "zsh: command not found: python"}
        )

        with pytest.raises(RuntimeError, match="Run python script"):
            await _require_command(
                sandbox_client,
                "sandbox-1",
                ["python", "main.py"],
                "/workspace/repo",
                label="Run python script",
            )

    @pytest.mark.asyncio
    async def test_require_command_passes_on_stdout(self, sandbox_client):
        sandbox_client.exec = AsyncMock(
            return_value={"exit_code": 0, "stdout": "Hello World!"}
        )

        result = await _require_command(
            sandbox_client,
            "sandbox-1",
            ["python", "main.py"],
            "/workspace/repo",
            label="Run python script",
        )

        assert result.get("exit_code") == 0
        assert result.get("stdout") == "Hello World!"


class TestProcessJob:
    """Tests:
    - field validation
    - job type verification with whats configured
    - payload validation - ensure set_state is called on invalid payload
    - successfull review_pull_request call on correct fields & payload
    """

    example_good_payload = '{"repository":"owner/repo","pull_request":2}'
    missing_required_fields: ClassVar = [
        {"type": "review", "payload": example_good_payload},
        {"job_id": "job-1", "payload": example_good_payload},
        {"job_id": "job-1", "type": "review"},
    ]

    @pytest.fixture
    def config(self, make_config: ConfigFactory):
        return make_config(review_job_name="review")

    @pytest.fixture
    def state_client(self):
        return AsyncMock(spec=ReviewStateClient)

    @pytest.mark.parametrize("job_fields", missing_required_fields)
    @pytest.mark.asyncio
    async def test_process_job_raises_on_missing_fields(
        self,
        job_fields,
        config,
        state_client,
    ):

        with pytest.raises(
            InvalidJobError, match="Job message is missing required fields or JSON"
        ):
            await process_job(
                job_fields,
                config,
                state_client=state_client,
                github_client=AsyncMock(),
            )

    @pytest.mark.asyncio
    async def test_process_job_raises_on_wrong_job_type(self, config, state_client):
        test_fields = {
            "job_id": "job-1",
            "type": "BAD",
            "payload": self.example_good_payload,
        }

        with pytest.raises(InvalidJobError, match="Unknown job type"):
            await process_job(
                test_fields,
                config,
                state_client=state_client,
                github_client=AsyncMock(),
            )

    @pytest.mark.asyncio
    async def test_process_job_returns_on_invalid_payload(self, config, state_client):

        test_fields = {
            "job_id": "job-1",
            "type": "review",
            "payload": '{"repository":"owner/repo","pr":2}',
        }

        await process_job(
            test_fields,
            config,
            state_client=state_client,
            github_client=AsyncMock(),
        )

        state_client.set_state.assert_awaited_once_with(
            "job-1",
            "failed",
            error="The queued review payload is invalid.",
        )

    @pytest.mark.asyncio
    async def test_valid_job_successfully_calls_review(
        self, monkeypatch, config, state_client
    ):
        review = AsyncMock()
        monkeypatch.setattr(worker, "review_pull_request", review)

        github_client = AsyncMock()

        await process_job(
            {
                "job_id": "job-1",
                "type": "review",
                "payload": self.example_good_payload,
            },
            config,
            state_client,
            github_client,
        )

        review.assert_called_once_with(
            "job-1",
            json.loads(self.example_good_payload),
            config,
            state_client,
            github_client,
        )


class TestProcessMessage:
    """Verifies queue task acknowledgment flow
    - acknowledges on successful processing
    - acknowledges on failed because of invalid fields
    - does not acknowledge on other errors
    """

    @pytest.fixture
    def config(self, make_config: ConfigFactory):
        return make_config(review_job_name="review")

    @pytest.fixture
    def redis(self, monkeypatch):
        mocked_redis = AsyncMock(spec=Redis)

        x_ack_call = AsyncMock(return_value=1)
        monkeypatch.setattr(mocked_redis, "xack", x_ack_call)
        return mocked_redis

    @pytest.fixture
    def state_client(self):
        return AsyncMock(spec=ReviewStateClient)

    @pytest.fixture
    def github_client(self):
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_process_message_acknowledges_successful_job(
        self, monkeypatch, config, redis, state_client, github_client
    ):
        """verify that XACK is called after successful process_job"""
        process_job = AsyncMock(return_value=None)
        monkeypatch.setattr(worker, "process_job", process_job)

        fields = {
            "job_id": "job-1",
            "type": config.review_job_name,
            "payload": json.dumps({"repository": "owner/repo", "pull_request": 2}),
        }

        await process_message(
            redis, config, state_client, github_client, "123-456", fields
        )

        process_job.assert_awaited_once_with(
            fields,
            config,
            state_client,
            github_client,
        )
        redis.xack.assert_awaited_once_with(
            config.job_stream,
            config.group_name,
            "123-456",
        )

    @pytest.mark.asyncio
    async def test_process_message_acknowledges_invalid_job_inputs(
        self, monkeypatch, config, redis, state_client, github_client
    ):
        """verify that XACK is called after invalid job fields are passed"""
        process_job = AsyncMock(side_effect=InvalidJobError("Unknown job type"))
        monkeypatch.setattr(worker, "process_job", process_job)

        fields = {
            "job_id": "job-1",
            "type": "INVALID-TYPE",
            "payload": json.dumps({"repository": "owner/repo", "pull_request": 2}),
        }

        await process_message(
            redis, config, state_client, github_client, "123-456", fields
        )

        process_job.assert_awaited_once_with(
            fields,
            config,
            state_client,
            github_client,
        )
        redis.xack.assert_awaited_once_with(
            config.job_stream,
            config.group_name,
            "123-456",
        )

    @pytest.mark.asyncio
    async def test_process_message_does_not_acknowledge_recoverable_error(
        self, monkeypatch, config, redis, state_client, github_client
    ):
        """verify that XACK is NOT called after other error, which we assume can be recovered.
        This covers other errors that `review_pull_request` might throw when a service is unavailable.
        """
        process_job = AsyncMock(side_effect=RuntimeError("Service unavailable"))
        monkeypatch.setattr(worker, "process_job", process_job)

        fields = {
            "job_id": "job-1",
            "type": "INVALID-TYPE",
            "payload": json.dumps({"repository": "owner/repo", "pull_request": 2}),
        }

        await process_message(
            redis, config, state_client, github_client, "123-456", fields
        )

        process_job.assert_awaited_once_with(
            fields,
            config,
            state_client,
            github_client,
        )
        redis.xack.assert_not_awaited()
