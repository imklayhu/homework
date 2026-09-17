from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.config import Settings, get_settings
from app.db import get_session
from app.main import app
from app.models import Video


FIXTURE = Path(__file__).parent / "fixtures" / "sample.mp4"


def make_client(tmp_path: Path) -> tuple[TestClient, Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    settings = Settings(
        data_dir=tmp_path,
        database_url="sqlite://",
        min_duration_seconds=1,
        max_duration_seconds=10,
    )
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app), session


def test_upload_creates_video_and_job(tmp_path: Path) -> None:
    client, session = make_client(tmp_path)
    with FIXTURE.open("rb") as source:
        response = client.post(
            "/api/videos",
            files={"file": ("../../lesson.mp4", source, "video/mp4")},
        )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "uploaded"
    video = session.get(Video, body["video_id"])
    assert video is not None
    assert ".." not in video.storage_key
    assert (tmp_path / video.storage_key).is_file()
    app.dependency_overrides.clear()


def test_video_content_uses_registered_storage_key(tmp_path: Path) -> None:
    client, session = make_client(tmp_path)
    stored = tmp_path / "uploads" / "video-id" / "source.mp4"
    stored.parent.mkdir(parents=True)
    stored.write_bytes(FIXTURE.read_bytes())
    video = Video(
        id="video-id",
        original_name="lesson.mp4",
        storage_key="uploads/video-id/source.mp4",
        duration_ms=4_000,
        size_bytes=stored.stat().st_size,
        mime_type="video/mp4",
        width=640,
        height=360,
    )
    session.add(video)
    session.commit()

    response = client.get("/api/videos/video-id/content")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("video/mp4")
    app.dependency_overrides.clear()
