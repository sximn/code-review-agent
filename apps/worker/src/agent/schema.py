from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

SupportedProviders = Literal["openai"]
CostStatus = Literal[
    "estimated",
    "unsupported-model",
    "usage-unavailable",
    "not-applicable",
]


class PRMetadata(BaseModel):
    title: str
    description: str
    diff: str


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Literal["quality", "performance", "security"]
    severity: Literal["critical", "high", "medium", "low"]
    title: str
    description: str
    file: str
    line_start: int | None
    line_end: int | None
    evidence: str
    recommendation: str
    confidence: float = Field(ge=0, le=1)


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid")

    findings: list[Finding]
    approval_granted: bool


class ModelUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    request_count: int = Field(ge=0)
    responses_with_usage: int = Field(ge=0)

    input_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(ge=0)
    cache_write_tokens: int = Field(ge=0)

    output_tokens: int = Field(ge=0)
    reasoning_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class ReviewUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: SupportedProviders = "openai"

    request_count: int = Field(ge=0)
    responses_with_usage: int = Field(ge=0)
    responses_without_usage: int = Field(ge=0)

    input_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(ge=0)
    cache_write_tokens: int = Field(ge=0)

    output_tokens: int = Field(ge=0)
    reasoning_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)

    models: list[ModelUsage]


class ReviewCost(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: CostStatus

    # Pydantic will serialize Decimal as string in JSON
    estimated_usd: Decimal | None
    pricing_version: str | None
    partial: bool
    unsupported_models: list[str] = Field(default_factory=list)

    @field_serializer("estimated_usd", when_used="json")
    def _serialize_usd(self, value: Decimal | None) -> str | None:
        return None if value is None else format(value, "f")
