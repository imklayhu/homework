import math
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response, status
from sqlmodel import Session

from app.config import Settings, get_settings
from app.db import get_session
from app.errors import AppError
from app.routes.videos import register_uploaded_video
from app.schemas import ChunkUploadCreated, ChunkUploadInit, UploadAccepted
from app.services.chunk_uploads import assemble_chunks, cleanup_expired_sessions, create_session, load_manifest, remove_session, write_chunk
from app.services.media import ALLOWED_MIME_TYPES


router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.post("/init", response_model=ChunkUploadCreated, status_code=status.HTTP_201_CREATED)
def initialize_upload(payload: ChunkUploadInit, settings: Settings = Depends(get_settings)) -> ChunkUploadCreated:
    original_name = Path(payload.filename).name
    if payload.content_type not in ALLOWED_MIME_TYPES or Path(original_name).suffix.lower() not in {".mp4", ".mov", ".webm"}:
        raise AppError("UNSUPPORTED_FORMAT", "仅支持 MP4、MOV 和 WebM 视频。")
    if payload.size_bytes > settings.max_upload_bytes:
        raise AppError("FILE_TOO_LARGE", "视频大小不能超过 300 MB。", 413)
    if payload.chunk_size > settings.chunk_upload_size:
        raise AppError("INVALID_CHUNK_SIZE", "单个分片不能超过 8 MB。")
    if payload.total_chunks != math.ceil(payload.size_bytes / payload.chunk_size):
        raise AppError("INVALID_CHUNK_COUNT", "分片数量与文件大小不一致。")
    settings.ensure_directories()
    cleanup_expired_sessions(settings.chunk_uploads_dir, settings.chunk_upload_ttl_seconds)
    manifest = create_session(settings.chunk_uploads_dir, original_name, payload.content_type, payload.size_bytes, payload.chunk_size, payload.total_chunks)
    return ChunkUploadCreated(upload_id=manifest.upload_id, chunk_size=manifest.chunk_size, total_chunks=manifest.total_chunks)


@router.put("/{upload_id}/chunks/{index}", status_code=status.HTTP_204_NO_CONTENT)
async def upload_chunk(upload_id: str, index: int, request: Request, settings: Settings = Depends(get_settings)) -> Response:
    manifest = load_manifest(settings.chunk_uploads_dir, upload_id)
    content = await request.body()
    write_chunk(settings.chunk_uploads_dir, manifest, index, content)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{upload_id}/complete", response_model=UploadAccepted, status_code=status.HTTP_202_ACCEPTED)
def complete_upload(upload_id: str, background_tasks: BackgroundTasks, session: Session = Depends(get_session), settings: Settings = Depends(get_settings)) -> UploadAccepted:
    manifest = load_manifest(settings.chunk_uploads_dir, upload_id)
    assembled = assemble_chunks(settings.chunk_uploads_dir, manifest)
    result = register_uploaded_video(assembled, manifest.filename, manifest.content_type, manifest.size_bytes, background_tasks, session, settings)
    remove_session(settings.chunk_uploads_dir, upload_id)
    return result
