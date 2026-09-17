from app.services.cost import Pricing, estimate_cost


def test_cost_uses_configured_token_rates() -> None:
    cost = estimate_cost(
        {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000},
        Pricing(input_per_million=0.8, output_per_million=2.7),
    )
    assert cost == 3.5


def test_cost_is_unknown_when_usage_is_incomplete() -> None:
    assert estimate_cost({"total_tokens": 100}, Pricing(0.8, 2.7)) is None
