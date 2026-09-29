from dataclasses import dataclass

from openai.types.chat import ChatCompletion

from .schema import ModelUsage, ReviewUsage


@dataclass(slots=True)
class _MutableModelUsage:
    request_count: int = 0
    responses_with_usage: int = 0

    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0

    output_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0


class UsageAccumulator:
    def __init__(self) -> None:
        self._models: dict[str, _MutableModelUsage] = {}

    def record(
        self,
        model: str,
        *,
        input_tokens: int | None = None,
        cached_input_tokens: int | None = None,
        cache_write_tokens: int | None = None,
        output_tokens: int | None = None,
        reasoning_tokens: int | None = None,
        total_tokens: int | None = None,
    ):
        model_usage = self._models.setdefault(model, _MutableModelUsage())
        model_usage.request_count += 1

        token_values = (
            input_tokens,
            cached_input_tokens,
            cache_write_tokens,
            output_tokens,
            reasoning_tokens,
            total_tokens,
        )

        # we received response, but it did not contain usage
        if all(value is None for value in token_values):
            return

        if any(value is None for value in token_values):
            raise ValueError(
                f"Token usage must be supplied completely or not at all | {input_tokens=} {cached_input_tokens=} {cache_write_tokens=} {output_tokens=} {reasoning_tokens=} {total_tokens=}"
            )

        assert input_tokens is not None
        assert cached_input_tokens is not None
        assert cache_write_tokens is not None
        assert output_tokens is not None
        assert reasoning_tokens is not None
        assert total_tokens is not None
        token_values = (
            input_tokens,
            cached_input_tokens,
            cache_write_tokens,
            output_tokens,
            reasoning_tokens,
            total_tokens,
        )

        if min(token_values) < 0:
            raise ValueError("Token counts cannot be negative")

        model_usage.responses_with_usage += 1
        model_usage.input_tokens += input_tokens
        model_usage.cached_input_tokens += cached_input_tokens
        model_usage.cache_write_tokens += cache_write_tokens
        model_usage.output_tokens += output_tokens
        model_usage.reasoning_tokens += reasoning_tokens
        model_usage.total_tokens += total_tokens

    def materialize(
        self,
    ) -> ReviewUsage:
        models: list[ModelUsage] = [
            ModelUsage(
                model=model_name,
                request_count=accumulated_model_usage.request_count,
                responses_with_usage=accumulated_model_usage.responses_with_usage,
                input_tokens=accumulated_model_usage.input_tokens,
                cached_input_tokens=accumulated_model_usage.cached_input_tokens,
                cache_write_tokens=accumulated_model_usage.cache_write_tokens,
                output_tokens=accumulated_model_usage.output_tokens,
                reasoning_tokens=accumulated_model_usage.reasoning_tokens,
                total_tokens=accumulated_model_usage.total_tokens,
            )
            for model_name, accumulated_model_usage in self._models.items()
        ]

        request_count = sum(model.request_count for model in models)
        responses_with_usage = sum(model.responses_with_usage for model in models)

        return ReviewUsage(
            request_count=request_count,
            responses_with_usage=responses_with_usage,
            responses_without_usage=request_count - responses_with_usage,
            input_tokens=sum(model.input_tokens for model in models),
            cached_input_tokens=sum(model.cached_input_tokens for model in models),
            cache_write_tokens=sum(model.cache_write_tokens for model in models),
            output_tokens=sum(model.output_tokens for model in models),
            reasoning_tokens=sum(model.reasoning_tokens for model in models),
            total_tokens=sum(model.total_tokens for model in models),
            models=models,
        )


def record_chat_completion_usage(
    accumulator: UsageAccumulator, response: ChatCompletion
) -> None:
    usage = response.usage

    if usage is None:
        accumulator.record(model=response.model)
        return

    prompt_details = usage.prompt_tokens_details
    completion_details = usage.completion_tokens_details

    accumulator.record(
        model=response.model,
        input_tokens=usage.prompt_tokens,
        cached_input_tokens=(
            (prompt_details.cached_tokens if prompt_details is not None else 0) or 0
        ),
        cache_write_tokens=(
            (prompt_details.cache_write_tokens if prompt_details is not None else 0)
            or 0
        ),
        output_tokens=usage.completion_tokens,
        reasoning_tokens=(
            (
                completion_details.reasoning_tokens
                if completion_details is not None
                else 0
            )
            or 0
        ),
        total_tokens=usage.total_tokens,
    )
