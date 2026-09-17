from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class JobStatus(StrEnum):
    UPLOADED = "uploaded"
    PREPROCESSING = "preprocessing"
    UNDERSTANDING = "understanding"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class TimeRange(BaseModel):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_range(self) -> "TimeRange":
        if self.start_ms >= self.end_ms:
            raise ValueError("start_ms must be less than end_ms")
        return self


class Chapter(TimeRange):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)


class Insight(TimeRange):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    transcript_evidence: str = ""
    visual_evidence: str = ""
    evidence_types: list[Literal["transcript", "visual"]] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    remix_reason: str = Field(min_length=1)


class AnalysisPayload(BaseModel):
    summary: str = Field(min_length=1)
    chapters: list[Chapter] = Field(min_length=1, max_length=12)
    insights: list[Insight] = Field(min_length=1, max_length=12)


class VideoRead(BaseModel):
    id: str
    original_name: str
    duration_ms: int
    size_bytes: int
    mime_type: str
    width: int | None
    height: int | None


class AnalysisJobRead(BaseModel):
    id: str
    video_id: str
    status: JobStatus
    current_stage: JobStatus
    error_code: str | None
    error_message: str | None
    provider_usage: dict[str, Any] | None
    estimated_cost: float | None
    created_at: datetime
    updated_at: datetime


class UploadAccepted(BaseModel):
    video_id: str
    job_id: str
    status: JobStatus


class RemixStatus(StrEnum):
    QUEUED = "queued"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class RemixCreate(BaseModel):
    insight_ids: list[str] = Field(min_length=1, max_length=8)


class RemixJobRead(BaseModel):
    id: str
    video_id: str
    status: RemixStatus
    duration_ms: int | None
    download_url: str | None
    error_code: str | None
