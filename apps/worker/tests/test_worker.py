import json
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import AsyncMock, Mock, call

import httpx
import pytest
from redis.asyncio import Redis
from src import worker
from src.review_state_client import ReviewStateClient
from src.sandbox_client import SandboxClient
from src.worker import (
    InvalidJobError,
    _require_command,
    process_job,
    process_message,
    review_pull_request,
)
from tests.conftest import ConfigFactory


class TestHelperFunctions:
    @pytest.fixture
    def sandbox_client(self):
        return AsyncMock(SandboxClient)

    def test_config_raises_on_missing_key_during_live_mode(self, make_config):
        with pytest.raises(ValueError):
            _ = make_config(agent_mode="live", openai_api_key=None)

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


class TestPullRequestReview:
    @pytest.fixture
    def state_client(self):
        client = AsyncMock(spec=ReviewStateClient)

        async def set_state(job_id, status, **kwargs):
            return status

        client.set_state.side_effect = set_state
        return client

    @pytest.fixture
    def sandbox_client(self):
        client = Mock(spec=SandboxClient)

        repo_sizes = iter([100, 200])

        client.create.return_value = "sandbox-123"

        async def exec_command(
            sandbox_id,
            command,
            cwd="/workspace/repo",
            env=None,
        ):
            if command[:2] == ["du", "-sb"]:
                size = next(repo_sizes)
                return {
                    "exit_code": 0,
                    "stdout": f"{size}\t/workspace/repo\n",
                    "stderr": "",
                }

            return {
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
            }

        client.exec.side_effect = exec_command
        client.destroy.return_value = None
        client.close.return_value = None

        return client

    @pytest.fixture
    def payload(self):
        return SimpleNamespace(
            repository_owner="sximn",
            repository_name="code-review-agent",
            repository_handle="sximn/code-review-agent",
            pull_request_number=42,
        )

    @pytest.fixture
    def metadata(self):
        return SimpleNamespace(
            title="Improve widgets",
            description="A useful PR",
            diff="diff --git ...",
            base_sha="base123",
            head_sha="head456",
        )

    @pytest.fixture
    def github_client(self):
        return AsyncMock(spec=httpx.AsyncClient)

    def assert_failed(self, state_client, message: str) -> None:
        assert state_client.set_state.await_args_list == [
            call("job-1", "running"),
            call("job-1", "failed", error=message),
        ]

    # "happy path"
    @pytest.mark.asyncio
    async def test_successful_review(
        self,
        monkeypatch,
        payload,
        config,
        metadata,
        state_client,
        sandbox_client,
        github_client,
    ):

        fetch_metadata = AsyncMock(return_value=metadata)
        review_result = Mock()
        review_result.model_dump.return_value = {
            "summary": "Looks good",
            "findings": [],
        }
        run_review = AsyncMock(return_value=review_result)

        monkeypatch.setattr(worker, "fetch_pr_metadata", fetch_metadata)
        monkeypatch.setattr(worker, "run_mock_agent_review", run_review)

        await review_pull_request(
            "job-1",
            payload,
            config,
            sandbox_client,
            state_client,
            github_client,
        )

        assert state_client.set_state.await_args_list == [
            call("job-1", "running"),
            call(
                "job-1",
                "finished",
                result={
                    "summary": "Looks good",
                    "findings": [],
                },
            ),
        ]

        sandbox_client.create.assert_awaited_once_with("job-1")
        sandbox_client.destroy.assert_awaited_once_with("sandbox-123")
        sandbox_client.close.assert_awaited_once_with()

        commands = [
            invocation.args[1] for invocation in sandbox_client.exec.await_args_list
        ]

        assert commands == [
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--no-checkout",
                "https://github.com/sximn/code-review-agent.git",
                "/workspace/repo",
            ],
            ["du", "-sb", "/workspace/repo"],
            [
                "git",
                "fetch",
                "--no-tags",
                "--depth=1",
                "origin",
                "base123",
            ],
            [
                "git",
                "fetch",
                "--no-tags",
                "--depth=1",
                "origin",
                "head456",
            ],
            ["git", "checkout", "--detach", "head456"],
            ["du", "-sb", "/workspace/repo"],
        ]

        fetch_metadata.assert_awaited_once_with(
            github_client,
            payload,
            config.github_token,
        )
        run_review.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fetch_metadata_failure(
        self,
        monkeypatch,
        payload,
        config,
        state_client,
        sandbox_client,
        github_client,
    ):
        fetch_metadata = AsyncMock(side_effect=RuntimeError("GitHub unavailable"))
        monkeypatch.setattr(
            worker,
            "fetch_pr_metadata",
            fetch_metadata,
        )

        await review_pull_request(
            "job-1",
            payload,
            config,
            sandbox_client,
            state_client,
            github_client,
        )

        self.assert_failed(state_client, "GitHub unavailable")

        sandbox_client.create.assert_not_awaited()
        sandbox_client.destroy.assert_not_awaited()
        sandbox_client.close.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_sandbox_creation_failure(
        self,
        monkeypatch,
        payload,
        config,
        metadata,
        state_client,
        sandbox_client,
        github_client,
    ):
        monkeypatch.setattr(
            worker,
            "fetch_pr_metadata",
            AsyncMock(return_value=metadata),
        )
        sandbox_client.create.side_effect = RuntimeError("Sandbox service unavailable")

        await review_pull_request(
            "job-1",
            payload,
            config,
            sandbox_client,
            state_client,
            github_client,
        )

        self.assert_failed(state_client, "Sandbox service unavailable")

        sandbox_client.destroy.assert_not_awaited()
        sandbox_client.close.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_checkout_failure(
        self,
        monkeypatch,
        payload,
        config,
        metadata,
        state_client,
        sandbox_client,
        github_client,
    ):
        monkeypatch.setattr(
            worker,
            "fetch_pr_metadata",
            AsyncMock(return_value=metadata),
        )

        async def exec_command(
            sandbox_id,
            command,
            cwd="/workspace/repo",
            env=None,
        ):
            if command[:2] == ["du", "-sb"]:
                return {
                    "exit_code": 0,
                    "stdout": "100\t/workspace/repo\n",
                    "stderr": "",
                }

            if command[:3] == ["git", "checkout", "--detach"]:
                return {
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": "invalid revision",
                }

            return {
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
            }

        sandbox_client.exec.side_effect = exec_command
        run_review = AsyncMock()
        monkeypatch.setattr(
            worker,
            "run_mock_agent_review",
            run_review,
        )

        await review_pull_request(
            "job-1",
            payload,
            config,
            sandbox_client,
            state_client,
            github_client,
        )

        self.assert_failed(
            state_client,
            "Pull request checkout failed: invalid revision",
        )

        sandbox_client.destroy.assert_awaited_once_with("sandbox-123")
        sandbox_client.close.assert_awaited_once_with()
        run_review.assert_not_awaited()

    @pytest.mark.parametrize(
        "failed_command,expected_error",
        [
            (
                ["git", "clone"],
                "Repository clone failed: simulated failure",
            ),
            (
                ["git", "fetch"],
                "Pull request base fetch failed: simulated failure",
            ),
            (
                ["git", "checkout"],
                "Pull request checkout failed: simulated failure",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_git_command_failure(
        self,
        monkeypatch,
        failed_command,
        expected_error,
        payload,
        config,
        metadata,
        sandbox_client,
        state_client,
        github_client,
    ):
        monkeypatch.setattr(
            worker,
            "fetch_pr_metadata",
            AsyncMock(return_value=metadata),
        )

        async def exec_command(
            sandbox_id,
            command,
            cwd="/workspace/repo",
            env=None,
        ):
            if command[: len(failed_command)] == failed_command:
                return {
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": "simulated failure",
                }

            # make the `du` command pass
            if command[:2] == ["du", "-sb"]:
                return {
                    "exit_code": 0,
                    "stdout": "100\t/workspace/repo\n",
                    "stderr": "",
                }

            return {
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
            }

        sandbox_client.exec.side_effect = exec_command

        await review_pull_request(
            "job-1",
            payload,
            config,
            sandbox_client,
            state_client,
            github_client,
        )

        self.assert_failed(state_client, expected_error)
        sandbox_client.destroy.assert_awaited_once_with("sandbox-123")
        sandbox_client.close.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_agent_failure(
        self,
        monkeypatch,
        payload,
        config,
        metadata,
        state_client,
        sandbox_client,
        github_client,
    ):
        monkeypatch.setattr(
            worker,
            "fetch_pr_metadata",
            AsyncMock(return_value=metadata),
        )
        monkeypatch.setattr(
            worker,
            "run_mock_agent_review",
            AsyncMock(side_effect=RuntimeError("Agent crashed")),
        )

        await review_pull_request(
            "job-1",
            payload,
            config,
            sandbox_client,
            state_client,
            github_client,
        )

        self.assert_failed(state_client, "Agent crashed")
        sandbox_client.destroy.assert_awaited_once_with("sandbox-123")
        sandbox_client.close.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_timeout_failure(
        self,
        monkeypatch,
        payload,
        config,
        state_client,
        sandbox_client,
        github_client,
    ):
        monkeypatch.setattr(
            worker,
            "fetch_pr_metadata",
            AsyncMock(side_effect=TimeoutError),
        )

        await review_pull_request(
            "job-1",
            payload,
            config,
            sandbox_client,
            state_client,
            github_client,
        )

        self.assert_failed(
            state_client,
            (f"The review exceeded the {config.job_timeout_seconds}-second deadline."),
        )
        sandbox_client.destroy.assert_not_awaited()
        sandbox_client.close.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_destroy_failure_does_not_hide_result(
        self,
        monkeypatch,
        payload,
        config,
        metadata,
        state_client,
        sandbox_client,
        github_client,
    ):
        monkeypatch.setattr(
            worker,
            "fetch_pr_metadata",
            AsyncMock(return_value=metadata),
        )

        review = Mock()
        review.model_dump.return_value = {"summary": "OK"}
        monkeypatch.setattr(
            worker,
            "run_mock_agent_review",
            AsyncMock(return_value=review),
        )

        sandbox_client.destroy.side_effect = RuntimeError("Destroy failed")

        await review_pull_request(
            "job-1",
            payload,
            config,
            sandbox_client,
            state_client,
            github_client,
        )

        assert state_client.set_state.await_args_list[-1] == call(
            "job-1",
            "finished",
            result={"summary": "OK"},
        )
        # successfully closed even if destroy fails
        sandbox_client.close.assert_awaited_once_with()
