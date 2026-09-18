import pytest
from pydantic import ValidationError

from sqlmodel import SQLModel, Session, create_engine, select
from sqlmodel.pool import StaticPool

from app.models import AnalysisJob, AnalysisJobLog, Video
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


def test_analysis_job_persists_progress_and_logs() -> None:
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        video = Video(id="video", original_name="lesson.mp4", storage_key="lesson.mp4", duration_ms=60_000, size_bytes=1, mime_type="video/mp4")
        job = AnalysisJob(video_id=video.id)
        log = AnalysisJobLog(job_id=job.id, stage="understanding", message="正在理解第 1/3 个片段")
        job.progress_current = 1
        job.progress_total = 3
        job.progress_percent = 33
        session.add(video)
        session.add(job)
        session.add(log)
        session.commit()

        stored_job = session.get(AnalysisJob, job.id)
        stored_log = session.get(AnalysisJobLog, log.id)
        assert stored_job is not None
        assert (stored_job.progress_current, stored_job.progress_total, stored_job.progress_percent) == (1, 3, 33)
        assert stored_log is not None
        assert stored_log.message == "正在理解第 1/3 个片段"
