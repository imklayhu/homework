import pytest
from pydantic import ValidationError

from app.schemas import AnalysisPayload, Insight, JobStatus


def valid_insight() -> dict:
    return {
        "id": "insight_01",
        "title": "行为证据比口头意愿更可靠",
        "explanation": "用行为数据交叉验证用户表达。",
        "start_ms": 10_000,
        "end_ms": 30_000,
        "transcript_evidence": "不要只问用户会不会买。",
        "visual_evidence": "PPT 对比了 Say 与 Do。",
        "evidence_types": ["transcript", "visual"],
        "confidence": 0.9,
        "remix_reason": "观点完整，适合独立传播。",
    }


def test_insight_rejects_reversed_time_range() -> None:
    data = valid_insight()
    data["end_ms"] = data["start_ms"]

    with pytest.raises(ValidationError):
        Insight.model_validate(data)


def test_analysis_payload_rejects_confidence_above_one() -> None:
    data = valid_insight()
    data["confidence"] = 1.1

    with pytest.raises(ValidationError):
        Insight.model_validate(data)


def test_analysis_payload_requires_chapters_and_insights() -> None:
    with pytest.raises(ValidationError):
        AnalysisPayload(summary="summary", chapters=[], insights=[])


def test_job_status_is_constrained() -> None:
    assert JobStatus.COMPLETED.value == "completed"
