from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReviewCompletion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    status: Literal["failed", "finished"]
    result: dict[str, Any] | None = None
    error: str | None = None
    usage: dict[str, Any] | None = None
    cost: dict[str, Any] | None = None
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    delivery_attempts: int = Field(default=0, ge=0)
    last_delivery_error: str | None = None

    @model_validator(mode="after")
    def validate_terminal_payload(self) -> "ReviewCompletion":
        if self.status == "finished":
            if self.result is None:
                raise ValueError("A finished review completion requires a result")
            if self.error is not None:
                raise ValueError("A finished review completion cannot contain an error")
        else:
            if not self.error:
                raise ValueError("A failed review completion requires an error")
            if self.result is not None:
                raise ValueError("A failed review completion cannot contain a result")
        return self

    def state_kwargs(self) -> dict[str, Any]:
        return {
            "result": self.result,
            "error": self.error,
            "usage": self.usage,
            "cost": self.cost,
        }
