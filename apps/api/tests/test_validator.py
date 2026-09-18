import pytest

from app.errors import AppError
from app.schemas import AnalysisPayload
from app.services.validator import normalize_range, validate_and_normalize


def payload() -> AnalysisPayload:
    return AnalysisPayload.model_validate(
        {
            "summary": "summary",
            "chapters": [
                {"id": "c1", "title": "chapter", "summary": "summary", "start_ms": 0, "end_ms": 10_000}
            ],
            "insights": [
                {
                    "id": "i1", "title": "insight", "explanation": "explanation",
                    "start_ms": 500, "end_ms": 9_500, "transcript_evidence": "evidence",
                    "visual_evidence": "visual", "evidence_types": ["visual"],
                    "confidence": 0.9, "remix_reason": "reason"
                }
            ],
        }
    )


def test_padding_is_clamped_to_video_bounds() -> None:
    assert normalize_range(500, 9_500, duration_ms=10_000, padding_ms=1_000) == (0, 10_000)


def test_validator_normalizes_insight_without_mutating_input() -> None:
    original = payload()
    result = validate_and_normalize(original, duration_ms=10_000)

    assert original.insights[0].start_ms == 500
    assert result.payload.insights[0].start_ms == 0


def test_validator_expands_short_insight_before_padding() -> None:
    data = payload().model_dump()
    data["insights"][0]["start_ms"] = 0
    data["insights"][0]["end_ms"] = 4_000

    result = validate_and_normalize(AnalysisPayload.model_validate(data), duration_ms=30_000)

    assert result.payload.insights[0].start_ms == 0
    assert result.payload.insights[0].end_ms == 6_000


def test_validator_rejects_duplicate_ids() -> None:
    data = payload().model_dump()
    data["insights"].append(data["insights"][0])
    with pytest.raises(AppError, match="INVALID_MODEL_OUTPUT"):
        validate_and_normalize(AnalysisPayload.model_validate(data), duration_ms=10_000)


@pytest.mark.parametrize("start_ms,end_ms", [(1_000, 125_000)])
def test_validator_rejects_insights_outside_remix_duration_bounds(
    start_ms: int, end_ms: int
) -> None:
    data = payload().model_dump()
    data["insights"][0]["start_ms"] = start_ms
    data["insights"][0]["end_ms"] = end_ms

    with pytest.raises(AppError, match="INVALID_MODEL_OUTPUT"):
        validate_and_normalize(AnalysisPayload.model_validate(data), duration_ms=130_000)
