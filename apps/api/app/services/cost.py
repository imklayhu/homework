from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Pricing:
    input_per_million: float
    output_per_million: float


def estimate_cost(usage: dict[str, Any], pricing: Pricing) -> float | None:
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    if not isinstance(prompt_tokens, int) or not isinstance(completion_tokens, int):
        return None
    return round(
        prompt_tokens / 1_000_000 * pricing.input_per_million
        + completion_tokens / 1_000_000 * pricing.output_per_million,
        6,
    )
