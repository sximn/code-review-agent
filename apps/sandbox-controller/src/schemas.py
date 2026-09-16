from pydantic import BaseModel, Field, field_validator


class CreateSandboxRequest(BaseModel):
    pass


class CreateSandboxResponse(BaseModel):
    id: str


class ExecCommandRequest(BaseModel):
    command: list[str] = Field(min_length=1, max_length=64)
    cwd: str = "/workspace/repo"
    env: dict[str, str] | None = None
    timeout_seconds: int | None = Field(default=None, ge=1, le=60)

    @field_validator("command")
    @classmethod
    def command_size(cls, value: list[str]) -> list[str]:
        if any(not item or len(item) > 4096 for item in value):
            raise ValueError(
                "Command arguments must be non-empty and max 4096 characters"
            )
        return value


class ExecCommandResponse(BaseModel):
    exit_code: int
    stdout: str
    stderr: str
    truncated: bool
    """
    whether the output was too long and was truncated before passing to the response
    """
