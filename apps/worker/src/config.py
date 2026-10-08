from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    agent_mode: Literal["live", "mock"] = Field(default="mock")
    openai_api_key: str | None = None
    model: str = Field(default="gpt-4o-mini", min_length=1)
    github_token: str | None = None

    redis_url: str = Field(min_length=1)
    web_service_url: str = Field(min_length=1)
    worker_api_token: str = Field(min_length=32)

    job_stream: str = Field(min_length=1)
    group_name: str = Field(min_length=1)
    review_job_name: str = Field(min_length=1)
    job_reclaim_timeout_seconds: int = Field()
    recovery_interval_seconds: int = Field()

    job_timeout_seconds: int = Field(default=300)
    max_repo_size_bytes: int = Field(default=400 * 1024 * 1024)
    max_steps: int = Field(default=30)

    sandbox_controller_url: str = Field(min_length=1)
    command_timeout_seconds: int = Field(default=60)
    sandbox_cleanup_timeout_seconds: float = Field(default=10)
    sandbox_controller_token: str = Field(min_length=1)
    worker_concurrency: int = Field(default=2, ge=1, le=16)

    completion_key_prefix: str = Field(default="review-completions", min_length=1)
    completion_dlq_stream: str = Field(default="review-completion-dlq", min_length=1)
    completion_ttl_seconds: int = Field(default=604800)
    completion_max_delivery_attempts: int = Field(default=5, ge=1)

    @model_validator(mode="after")
    def validate_live_agent_config(self) -> "AppConfig":
        if self.agent_mode == "live" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when AGENT_MODE=live")

        return self
