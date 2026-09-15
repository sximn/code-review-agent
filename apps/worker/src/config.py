from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    agent_mode: Literal["live", "mock"] = Field(default="mock")
    openai_api_key: str = Field(min_length=1)
    model: str = Field(min_length=1)

    redis_url: str = Field(min_length=1)

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
    sandbox_controller_token: str = Field(min_length=1)
