from dataclasses import dataclass

@dataclass(frozen=True)
class ModelPricing:
    input_per_1m: float
    cached_input_per_1m: float
    output_per_1m: float


PRICING: dict[str, ModelPricing] = {
    # GPT-5.4 family
    "gpt-5.4": ModelPricing(
        input_per_1m=2.50,
        cached_input_per_1m=0.25,
        output_per_1m=15.00,
    ),
    "gpt-5.4-mini": ModelPricing(
        input_per_1m=0.75,
        cached_input_per_1m=0.08,
        output_per_1m=4.50,
    ),
    "gpt-5.4-nano": ModelPricing(
        input_per_1m=0.20,
        cached_input_per_1m=0.02,
        output_per_1m=1.25,
    ),

    # GPT-4o family
    "gpt-4o": ModelPricing(
        input_per_1m=5.00,
        cached_input_per_1m=0.50,
        output_per_1m=15.00,
    ),
    "gpt-4o-mini": ModelPricing(
        input_per_1m=0.15,
        cached_input_per_1m=0.015,
        output_per_1m=0.60,
    ),

    # GPT-4.1 family
    "gpt-4.1": ModelPricing(
        input_per_1m=3.00,
        cached_input_per_1m=0.30,
        output_per_1m=12.00,
    ),
    "gpt-4.1-mini": ModelPricing(
        input_per_1m=0.60,
        cached_input_per_1m=0.06,
        output_per_1m=2.40,
    ),
    "gpt-4.1-nano": ModelPricing(
        input_per_1m=0.10,
        cached_input_per_1m=0.01,
        output_per_1m=0.40,
    ),
}


def estimate_cost(
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> tuple[float, float, float]:

    pricing = PRICING.get(model_name)
    if pricing is None:
        return 0.0, 0.0, 0.0

    non_cached_input_tokens = max(input_tokens - cached_input_tokens, 0)

    input_cost = (
        (non_cached_input_tokens / 1_000_000) * pricing.input_per_1m
        + (cached_input_tokens / 1_000_000) * pricing.cached_input_per_1m
    )
    output_cost = (output_tokens / 1_000_000) * pricing.output_per_1m
    total_cost = input_cost + output_cost

    return input_cost, output_cost, total_cost