from datetime import UTC, datetime
from uuid import uuid4

from sqlmodel import Field, SQLModel

from app.schemas import JobStatus, RemixStatus


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class Video(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    original_name: str
    storage_key: str = Field(index=True, unique=True)
    duration_ms: int
    size_bytes: int
    mime_type: str
    width: int | None = None
    height: int | None = None
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime | None = None


class AnalysisJob(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    video_id: str = Field(foreign_key="video.id", index=True)
    status: str = Field(default=JobStatus.UPLOADED.value, index=True)
    current_stage: str = Field(default=JobStatus.UPLOADED.value)
    provider_usage_json: str | None = None
    estimated_cost: float | None = None
    failed_stage: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    error_detail: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AnalysisResult(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    job_id: str = Field(foreign_key="analysisjob.id", index=True, unique=True)
    transcript_json: str | None = None
    visual_observations_json: str | None = None
    insights_json: str
    prompt_version: str
    model_version: str
    created_at: datetime = Field(default_factory=utc_now)


class RemixJob(SQLModel, table=True):
    id: str = Field(default_factory=new_id, primary_key=True)
    video_id: str = Field(foreign_key="video.id", index=True)
    selected_segments_json: str
    status: str = Field(default=RemixStatus.QUEUED.value, index=True)
    output_storage_key: str | None = None
    duration_ms: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    error_detail: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
