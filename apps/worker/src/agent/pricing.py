from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

from .schema import ReviewCost, ReviewUsage

PRICING_VERSION: Final = "2026-09-23"

MILLION_TOKENS: Final = Decimal(1_000_000)
USD_PRECISION: Final = Decimal("0.000000000001")


@dataclass(frozen=True, slots=True)
class ModelPrice:
    input_per_million: Decimal
    cached_input_per_million: Decimal
    output_per_million: Decimal
    cache_write_per_million: Decimal | None = None


GPT_4O_MINI_PRICE = ModelPrice(
    input_per_million=Decimal("0.15"),
    cached_input_per_million=Decimal("0.075"),
    output_per_million=Decimal("0.60"),
)


# explicit aliases and snapshots ()
MODEL_PRICING: dict[str, ModelPrice] = {
    "gpt-4o-mini": GPT_4O_MINI_PRICE,
    "gpt-4o-mini-2024-07-18": GPT_4O_MINI_PRICE,
}


def estimate_review_cost(
    usage: ReviewUsage,
    *,
    run_completed: bool,
) -> ReviewCost:
    partial = not run_completed or usage.responses_without_usage > 0

    if usage.responses_with_usage == 0:
        return ReviewCost(
            status="usage-unavailable",
            estimated_usd=None,
            pricing_version=PRICING_VERSION,
            partial=True,
        )

    unsupported_models: set[str] = set()
    total_usd = Decimal(0)

    for model_usage in usage.models:
        # nothing from this can be priced
        if model_usage.responses_with_usage == 0:
            continue

        price = MODEL_PRICING.get(model_usage.model)
        if price is None:
            unsupported_models.add(model_usage.model)
            continue

        if model_usage.cache_write_tokens > 0 and price.cache_write_per_million is None:
            unsupported_models.add(model_usage.model)
            continue

        uncached_input_tokens = (
            model_usage.input_tokens
            - model_usage.cached_input_tokens
            - model_usage.cache_write_tokens
        )

        total_usd += (
            Decimal(uncached_input_tokens) * price.input_per_million / MILLION_TOKENS
        )

        total_usd += (
            Decimal(model_usage.cached_input_tokens)
            * price.cached_input_per_million
            / MILLION_TOKENS
        )

        if model_usage.cache_write_tokens > 0:
            assert price.cache_write_per_million is not None

            total_usd += (
                Decimal(model_usage.cache_write_tokens)
                * price.cache_write_per_million
                / MILLION_TOKENS
            )

        # reasoning tokens are already part of the output_tokens, so we do not calculate them separately
        total_usd += (
            Decimal(model_usage.output_tokens)
            * price.output_per_million
            / MILLION_TOKENS
        )

    if unsupported_models:
        return ReviewCost(
            status="unsupported-model",
            estimated_usd=None,
            pricing_version=PRICING_VERSION,
            partial=partial,
            unsupported_models=sorted(unsupported_models),
        )

    return ReviewCost(
        status="estimated",
        estimated_usd=total_usd.quantize(
            USD_PRECISION,
            rounding=ROUND_HALF_UP,
        ),
        pricing_version=PRICING_VERSION,
        partial=partial,
    )


def mock_review_cost() -> ReviewCost:
    return ReviewCost(
        status="not-applicable",
        estimated_usd=None,
        pricing_version=None,
        partial=False,
    )
