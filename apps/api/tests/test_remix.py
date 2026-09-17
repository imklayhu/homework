import json
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.errors import AppError
from app.models import AnalysisJob, AnalysisResult, RemixJob, Video
from app.services.media import probe_video
from app.services.remix import render_remix, resolve_segments


FIXTURE = Path(__file__).parent / "fixtures" / "sample.mp4"


def make_session(tmp_path: Path) -> tuple[Session, Video, AnalysisJob]:
    engine = create_engine("sqlite://", poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    stored = tmp_path / "uploads/video/source.mp4"
    stored.parent.mkdir(parents=True)
    stored.write_bytes(FIXTURE.read_bytes())
    video = Video(
        id="video", original_name="lesson.mp4", storage_key="uploads/video/source.mp4",
        duration_ms=4_000, size_bytes=stored.stat().st_size, mime_type="video/mp4",
        width=640, height=360,
    )
    job = AnalysisJob(id="analysis", video_id=video.id, status="completed", current_stage="completed")
    payload = {
        "summary": "summary",
        "chapters": [{"id":"c1","title":"chapter","summary":"summary","start_ms":0,"end_ms":4000}],
        "insights": [
            {"id":"i1","title":"one","explanation":"one","start_ms":0,"end_ms":2000,"transcript_evidence":"one","visual_evidence":"one","evidence_types":["visual"],"confidence":.9,"remix_reason":"one"},
            {"id":"i2","title":"two","explanation":"two","start_ms":2000,"end_ms":4000,"transcript_evidence":"two","visual_evidence":"two","evidence_types":["visual"],"confidence":.9,"remix_reason":"two"}
        ]
    }
    result = AnalysisResult(job_id=job.id, insights_json=json.dumps(payload), prompt_version="v1", model_version="model")
    session.add(video); session.add(job); session.add(result); session.commit()
    return session, video, job


def test_resolve_segments_uses_trusted_ids_in_requested_order(tmp_path: Path) -> None:
    session, video, _ = make_session(tmp_path)
    segments = resolve_segments(session, video.id, ["i2", "i1"])
    assert [segment.id for segment in segments] == ["i2", "i1"]


def test_resolve_segments_rejects_unknown_id(tmp_path: Path) -> None:
    session, video, _ = make_session(tmp_path)
    with pytest.raises(AppError, match="INVALID_INSIGHT"):
        resolve_segments(session, video.id, ["missing"])


def test_render_remix_creates_playable_mp4(tmp_path: Path) -> None:
    session, video, _ = make_session(tmp_path)
    remix = RemixJob(id="remix", video_id=video.id, selected_segments_json='["i2","i1"]')
    session.add(remix); session.commit()

    render_remix(remix.id, session, tmp_path)

    session.refresh(remix)
    output = tmp_path / remix.output_storage_key
    metadata = probe_video(output)
    assert remix.status == "completed"
    assert 3_500 <= metadata.duration_ms <= 4_500
    assert metadata.has_audio is True
