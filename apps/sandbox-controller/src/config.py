from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SandboxConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    sandbox_controller_token: str = Field(min_length=1)

    sandbox_image: str = Field(min_length=1)
    sandbox_runtime: str = Field(default="runsc", min_length=1)
    sandbox_memory: str = Field(default="1536m")  # 1.5MB
    sandbox_cpus: float = Field(default=1.0)
    sandbox_pids_limit: int = Field(default=128)
    sandbox_label_prefix: str = Field(default="code-review-agent")
    sandbox_network: str = Field(default="code-review-agent-sandbox")

    sandbox_command_timeout_seconds: int = Field(default=60)
    sandbox_max_lifetime_seconds: int = Field(default=600)
    sandbox_max_concurrent: int = Field(default=2)
