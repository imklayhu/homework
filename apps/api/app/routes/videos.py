import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from fastapi.responses import FileResponse
from sqlmodel import Session

from app.config import Settings, get_settings
from app.db import get_session
from app.errors import AppError
from app.models import AnalysisJob, Video
from app.schemas import JobStatus, UploadAccepted
from app.services.media import ALLOWED_MIME_TYPES, probe_video, validate_media
from app.services.analysis import execute_analysis_job
from app.services.analytics import record_event


router = APIRouter(prefix="/api", tags=["videos"])


def register_uploaded_video(
    source_path: Path,
    original_name: str,
    mime_type: str,
    size_bytes: int,
    background_tasks: BackgroundTasks,
    session: Session,
    settings: Settings,
) -> UploadAccepted:
    suffix = Path(original_name).suffix.lower()
    video_id = str(uuid4())
    upload_dir = settings.uploads_dir / video_id
    final_path = upload_dir / f"source{suffix}"
    metadata = probe_video(source_path)
    validate_media(Path(original_name), size_bytes, metadata.duration_ms, settings.max_upload_bytes, settings.min_duration_seconds, settings.max_duration_seconds)
    try:
        upload_dir.mkdir(parents=True, exist_ok=True)
        source_path.replace(final_path)
        storage_key = final_path.relative_to(settings.data_dir).as_posix()
        video = Video(id=video_id, original_name=original_name, storage_key=storage_key, duration_ms=metadata.duration_ms, size_bytes=size_bytes, mime_type=mime_type, width=metadata.width, height=metadata.height)
        job = AnalysisJob(video_id=video_id)
        session.add(video)
        session.add(job)
        session.commit()
        session.refresh(job)
        record_event(session, "video_upload_completed", {"video_id": video_id, "job_id": job.id, "size_bytes": video.size_bytes})
        session.commit()
        if settings.on_demand_api_key is not None and settings.on_demand_base_url:
            background_tasks.add_task(execute_analysis_job, job.id, settings)
        return UploadAccepted(video_id=video_id, job_id=job.id, status=JobStatus.UPLOADED)
    except Exception:
        session.rollback()
        if final_path.exists():
            shutil.rmtree(upload_dir, ignore_errors=True)
        raise


@router.post("/videos", response_model=UploadAccepted, status_code=status.HTTP_202_ACCEPTED)
def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> UploadAccepted:
    original_name = Path(file.filename or "video").name
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise AppError("UNSUPPORTED_FORMAT", "仅支持 MP4、MOV 和 WebM 视频。")

    video_id = str(uuid4())
    temp_path = settings.temp_dir / f"{video_id}.upload"
    settings.ensure_directories()

    size_bytes = 0
    try:
        with temp_path.open("wb") as destination:
            while chunk := file.file.read(1024 * 1024):
                size_bytes += len(chunk)
                if size_bytes > settings.max_upload_bytes:
                    raise AppError("FILE_TOO_LARGE", "视频大小不能超过 300 MB。")
                destination.write(chunk)

        return register_uploaded_video(temp_path, original_name, file.content_type, size_bytes, background_tasks, session, settings)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


@router.get("/videos/{video_id}/content")
def video_content(
    video_id: str,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    video = session.get(Video, video_id)
    if video is None:
        raise AppError("VIDEO_NOT_FOUND", "视频不存在或已经过期。", 404)
    path = (settings.data_dir / video.storage_key).resolve()
    data_root = settings.data_dir.resolve()
    if not path.is_relative_to(data_root) or not path.is_file():
        raise AppError("VIDEO_NOT_FOUND", "视频不存在或已经过期。", 404)
    return FileResponse(path, media_type=video.mime_type, filename=video.original_name)
