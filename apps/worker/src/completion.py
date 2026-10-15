from datetime import UTC, datetime
from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
    model_validator,
)

CommitSha = Annotated[
    str,
    StringConstraints(strict=True, pattern=r"^([0-9a-f]{40}|[0-9a-f]{64})$"),
]


class CompletionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["failed", "finished"]
    result: dict[str, Any] | None = None
    error: str | None = None
    usage: dict[str, Any] | None = None
    cost: dict[str, Any] | None = None
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    delivery_attempts: int = Field(default=0, ge=0)
    last_delivery_error: str | None = None

    @model_validator(mode="after")
    def validate_terminal_payload(self) -> Self:
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
            "completed_at": self.completed_at,
        }


class ReviewCompletionV1(CompletionBase):
    schema_version: Literal[1] = 1


class ReviewCompletionV2(CompletionBase):
    schema_version: Literal[2] = 2
    reviewed_head_sha: CommitSha | None = None

    @model_validator(mode="after")
    def validate_reviewed_commit(self) -> Self:
        if self.status == "finished" and self.reviewed_head_sha is None:
            raise ValueError("A finished v2 completion requires reviewed_head_sha")

        return self

    def state_kwargs(self) -> dict[str, Any]:
        return {
            **super().state_kwargs(),
            "reviewed_head_sha": self.reviewed_head_sha,
        }


StoredReviewCompletion = Annotated[
    ReviewCompletionV1 | ReviewCompletionV2,
    Field(discriminator="schema_version"),
]

completion_adapter: TypeAdapter[StoredReviewCompletion] = TypeAdapter(
    StoredReviewCompletion
)

# newly executed jobs produce v2
ReviewCompletion = ReviewCompletionV2
