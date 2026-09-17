import json
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.errors import AppError
from app.models import AnalysisJob, AnalysisResult, Video
from app.schemas import JobStatus
from app.services.analysis import run_analysis
from app.services.bailian import ModelAnalysisResult
from app.schemas import AnalysisPayload


FIXTURE = Path(__file__).parent / "fixtures" / "sample.mp4"
MODEL_RESPONSE = Path(__file__).parent / "fixtures" / "qwen-response.json"


class FakeAdapter:
    async def analyze(self, video_url: str, duration_ms: int) -> ModelAnalysisResult:
        assert video_url.startswith("data:video/mp4;base64,")
        raw = json.loads(MODEL_RESPONSE.read_text())
        payload = AnalysisPayload.model_validate(json.loads(raw["choices"][0]["message"]["content"]))
        return ModelAnalysisResult(payload, raw["usage"], "qwen3-vl-flash", "qwen-video-v1")


class FailingAdapter:
    async def analyze(self, video_url: str, duration_ms: int) -> ModelAnalysisResult:
        raise AppError("MODEL_TIMEOUT", "视频分析超时，请重试。", 504)


def session_with_job(tmp_path: Path) -> tuple[Session, AnalysisJob]:
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    stored = tmp_path / "uploads" / "video" / "source.mp4"
    stored.parent.mkdir(parents=True)
    stored.write_bytes(FIXTURE.read_bytes())
    video = Video(
        id="video", original_name="lesson.mp4", storage_key="uploads/video/source.mp4",
        duration_ms=4_000, size_bytes=stored.stat().st_size, mime_type="video/mp4",
        width=640, height=360,
    )
    job = AnalysisJob(id="job", video_id=video.id)
    session.add(video)
    session.add(job)
    session.commit()
    return session, job


@pytest.mark.asyncio
async def test_run_analysis_persists_completed_result(tmp_path: Path) -> None:
    session, job = session_with_job(tmp_path)

    await run_analysis(job.id, session, tmp_path, FakeAdapter())

    session.refresh(job)
    result = session.exec(select(AnalysisResult).where(AnalysisResult.job_id == job.id)).one()
    assert job.status == JobStatus.COMPLETED.value
    assert result.model_version == "qwen3-vl-flash"
    assert json.loads(result.insights_json)["insights"][0]["id"] == "insight_01"
    assert job.provider_usage_json is not None


@pytest.mark.asyncio
async def test_run_analysis_records_failed_stage(tmp_path: Path) -> None:
    session, job = session_with_job(tmp_path)

    await run_analysis(job.id, session, tmp_path, FailingAdapter())

    session.refresh(job)
    assert job.status == JobStatus.FAILED.value
    assert job.failed_stage == JobStatus.UNDERSTANDING.value
    assert job.error_code == "MODEL_TIMEOUT"
    assert job.error_detail is None


def test_job_and_result_endpoints_return_persisted_data(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient
    from app.config import Settings, get_settings
    from app.db import get_session
    from app.main import app

    session, job = session_with_job(tmp_path)
    payload = json.loads(MODEL_RESPONSE.read_text())["choices"][0]["message"]["content"]
    job.status = JobStatus.COMPLETED.value
    job.current_stage = JobStatus.COMPLETED.value
    session.add(job)
    session.add(AnalysisResult(
        job_id=job.id, insights_json=payload, prompt_version="qwen-video-v1",
        model_version="qwen3-vl-flash"
    ))
    session.commit()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_settings] = lambda: Settings(data_dir=tmp_path)
    client = TestClient(app)

    job_response = client.get(f"/api/jobs/{job.id}")
    result_response = client.get(f"/api/jobs/{job.id}/result")

    assert job_response.status_code == 200
    assert job_response.json()["status"] == "completed"
    assert result_response.status_code == 200
    assert result_response.json()["insights"][0]["id"] == "insight_01"
    app.dependency_overrides.clear()
