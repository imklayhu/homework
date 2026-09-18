import json
import shutil
import time
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from app.errors import AppError


class UploadManifest(BaseModel):
    upload_id: str
    filename: str
    content_type: str
    size_bytes: int
    chunk_size: int
    total_chunks: int
    created_at: float


def session_dir(root: Path, upload_id: str) -> Path:
    return root / upload_id


def create_session(root: Path, filename: str, content_type: str, size_bytes: int, chunk_size: int, total_chunks: int) -> UploadManifest:
    upload_id = str(uuid4())
    directory = session_dir(root, upload_id)
    directory.mkdir(parents=True, exist_ok=False)
    manifest = UploadManifest(upload_id=upload_id, filename=filename, content_type=content_type, size_bytes=size_bytes, chunk_size=chunk_size, total_chunks=total_chunks, created_at=time.time())
    temp = directory / "manifest.json.tmp"
    temp.write_text(manifest.model_dump_json(), encoding="utf-8")
    temp.replace(directory / "manifest.json")
    return manifest


def load_manifest(root: Path, upload_id: str) -> UploadManifest:
    path = session_dir(root, upload_id) / "manifest.json"
    if not path.is_file():
        raise AppError("UPLOAD_NOT_FOUND", "上传会话不存在或已经过期。", 404)
    try:
        return UploadManifest.model_validate_json(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise AppError("UPLOAD_NOT_FOUND", "上传会话无效，请重新上传。", 404) from exc


def expected_chunk_size(manifest: UploadManifest, index: int) -> int:
    if index < 0 or index >= manifest.total_chunks:
        raise AppError("INVALID_CHUNK", "分片编号无效。")
    if index < manifest.total_chunks - 1:
        return manifest.chunk_size
    return manifest.size_bytes - manifest.chunk_size * (manifest.total_chunks - 1)


def write_chunk(root: Path, manifest: UploadManifest, index: int, content: bytes) -> None:
    expected = expected_chunk_size(manifest, index)
    if len(content) != expected:
        raise AppError("INVALID_CHUNK", f"分片大小无效，应为 {expected} 字节。")
    directory = session_dir(root, manifest.upload_id)
    temp = directory / f"{index}.part.tmp"
    temp.write_bytes(content)
    temp.replace(directory / f"{index}.part")


def assemble_chunks(root: Path, manifest: UploadManifest) -> Path:
    directory = session_dir(root, manifest.upload_id)
    parts = [directory / f"{index}.part" for index in range(manifest.total_chunks)]
    if any(not part.is_file() for part in parts):
        raise AppError("MISSING_CHUNKS", "仍有分片未上传，请重试。", 409)
    assembled = directory / "assembled.upload"
    temporary = directory / "assembled.upload.tmp"
    size = 0
    with temporary.open("wb") as destination:
        for index, part in enumerate(parts):
            if part.stat().st_size != expected_chunk_size(manifest, index):
                raise AppError("INVALID_CHUNK", "分片大小校验失败，请重新上传。")
            with part.open("rb") as source:
                while block := source.read(1024 * 1024):
                    size += len(block)
                    destination.write(block)
    if size != manifest.size_bytes:
        temporary.unlink(missing_ok=True)
        raise AppError("FILE_SIZE_MISMATCH", "合并后文件大小不一致，请重新上传。")
    temporary.replace(assembled)
    return assembled


def remove_session(root: Path, upload_id: str) -> None:
    shutil.rmtree(session_dir(root, upload_id), ignore_errors=True)


def cleanup_expired_sessions(root: Path, ttl_seconds: int, now: float | None = None) -> None:
    if not root.exists():
        return
    cutoff = (now or time.time()) - ttl_seconds
    for directory in root.iterdir():
        if directory.is_dir() and directory.stat().st_mtime < cutoff:
            shutil.rmtree(directory, ignore_errors=True)
