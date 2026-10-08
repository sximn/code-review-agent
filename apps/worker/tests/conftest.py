from collections.abc import Callable
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import fakeredis
import pytest
from src.config import AppConfig
from src.review_execution import ReviewExecutor
from src.sandbox_client import SandboxClient

ConfigFactory = Callable[..., AppConfig]


@pytest.fixture
def make_config() -> ConfigFactory:
    def factory(**overrides: Any) -> AppConfig:
        cfg = AppConfig(
            agent_mode="mock",
            openai_api_key=None,
            model="test-model",
            github_token=None,
            redis_url="redis://localhost:6379",
            web_service_url="https://web.test",
            worker_api_token="x" * 32,
            job_stream="review-jobs",
            group_name="review-workers",
            review_job_name="review",
            job_reclaim_timeout_seconds=600,
            recovery_interval_seconds=60,
            job_timeout_seconds=300,
            max_repo_size_bytes=400 * 1024 * 1024,
            max_steps=30,
            sandbox_controller_url="https://sandbox.test",
            command_timeout_seconds=60,
            sandbox_controller_token="sandbox-secret",
            worker_concurrency=2,
            completion_dlq_stream="dlq",
            completion_key_prefix="stream",
        )
        values = cfg.model_dump()
        values.update(overrides)
        return AppConfig.model_validate(values)

    return factory


@pytest.fixture
def config(make_config: ConfigFactory) -> AppConfig:
    return make_config()


@pytest.fixture
def redis_async_client() -> fakeredis.FakeAsyncRedis:

    redis_client = fakeredis.FakeAsyncRedis(
        server_type="dragonfly",
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=15,
    )
    return redis_client


@pytest.fixture
def review_execution(monkeypatch: pytest.MonkeyPatch, make_config) -> SimpleNamespace:
    config: AppConfig = make_config(
        github_token=None,
        job_timeout_seconds=1,
        max_repo_size_bytes=1000,
        agent_mode="mock",
        sandbox_cleanup_timeout_seconds=0.02,
    )
    sandbox = SimpleNamespace(
        create=AsyncMock(return_value="sandbox-1"),
        exec=AsyncMock(
            return_value={
                "exit_code": 0,
                "stdout": "100 /workspace/repo",
            }
        ),
        destroy=AsyncMock(),
        close=AsyncMock(),
    )
    payload = SimpleNamespace(
        repository_owner="owner",
        repository_name="repo",
        visibility="public",
    )
    metadata = SimpleNamespace(
        title="title",
        description="body",
        diff="diff",
        base_sha="base",
        head_sha="head",
    )
    review = SimpleNamespace(
        model_dump=lambda **kwargs: {"summary": "OK"},
    )
    fetch_metadata = AsyncMock(return_value=metadata)
    run_agent = AsyncMock(return_value=review)

    monkeypatch.setattr(
        "src.review_execution.fetch_pr_metadata",
        fetch_metadata,
    )
    monkeypatch.setattr(
        "src.review_execution.run_mock_agent_review",
        run_agent,
    )
    monkeypatch.setattr(
        "src.review_execution.mock_review_cost",
        lambda *args, **kwargs: None,
    )

    return SimpleNamespace(
        config=config,
        sandbox=sandbox,
        executor=ReviewExecutor(
            config, AsyncMock(), lambda: cast(SandboxClient, sandbox)
        ),
        payload=payload,
        metadata=fetch_metadata,
        agent=run_agent,
    )
