from collections.abc import Callable
from typing import Any

import pytest
from src.config import AppConfig

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
        )
        values = cfg.model_dump()
        values.update(overrides)
        return AppConfig.model_validate(values)

    return factory


@pytest.fixture
def config(make_config: ConfigFactory) -> AppConfig:
    return make_config()
