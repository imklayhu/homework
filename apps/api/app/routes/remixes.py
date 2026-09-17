import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from sqlmodel import Session

from app.config import Settings, get_settings
from app.db import get_session
from app.errors import AppError
from app.models import RemixJob, Video
from app.schemas import RemixCreate, RemixJobRead, RemixStatus
from app.services.remix import execute_remix_job, resolve_segments


router = APIRouter(prefix="/api", tags=["remixes"])


def serialize_remix(job: RemixJob) -> RemixJobRead:
    return RemixJobRead(
        id=job.id,
        video_id=job.video_id,
        status=RemixStatus(job.status),
        duration_ms=job.duration_ms,
        download_url=f"/api/remixes/{job.id}/download" if job.status == "completed" else None,
        error_code=job.error_code,
    )


@router.post("/videos/{video_id}/remixes", response_model=RemixJobRead, status_code=202)
def create_remix(
    video_id: str,
    body: RemixCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> RemixJobRead:
    video = session.get(Video, video_id)
    if video is None:
        raise AppError("VIDEO_NOT_FOUND", "视频不存在或已经过期。", 404)
    resolve_segments(session, video_id, body.insight_ids)
    job = RemixJob(video_id=video_id, selected_segments_json=json.dumps(body.insight_ids))
    session.add(job); session.commit(); session.refresh(job)
    background_tasks.add_task(execute_remix_job, job.id, settings.data_dir)
    return serialize_remix(job)


@router.get("/remixes/{remix_id}", response_model=RemixJobRead)
def get_remix(remix_id: str, session: Session = Depends(get_session)) -> RemixJobRead:
    job = session.get(RemixJob, remix_id)
    if job is None:
        raise AppError("REMIX_NOT_FOUND", "Remix 任务不存在。", 404)
    return serialize_remix(job)


@router.get("/remixes/{remix_id}/download")
def download_remix(
    remix_id: str,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    job = session.get(RemixJob, remix_id)
    if job is None or job.status != RemixStatus.COMPLETED.value or not job.output_storage_key:
        raise AppError("REMIX_NOT_READY", "Remix 尚未生成完成。", 409)
    path = (settings.data_dir / job.output_storage_key).resolve()
    if not path.is_relative_to(settings.data_dir.resolve()) or not path.is_file():
        raise AppError("REMIX_NOT_FOUND", "Remix 文件不存在或已经过期。", 404)
    return FileResponse(path, media_type="video/mp4", filename=f"remix-{remix_id[:8]}.mp4")
