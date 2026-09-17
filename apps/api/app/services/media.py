import json
import subprocess
from pathlib import Path

from pydantic import BaseModel

from app.errors import AppError


ALLOWED_EXTENSIONS = {".mp4", ".mov", ".webm"}
ALLOWED_MIME_TYPES = {"video/mp4", "video/quicktime", "video/webm"}


class MediaMetadata(BaseModel):
    duration_ms: int
    width: int
    height: int
    video_codec: str
    has_audio: bool


def probe_video(path: Path) -> MediaMetadata:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        data = json.loads(result.stdout)
        video_stream = next(
            stream for stream in data["streams"] if stream.get("codec_type") == "video"
        )
        duration = data.get("format", {}).get("duration") or video_stream.get("duration")
        if duration is None:
            raise ValueError("missing duration")
        return MediaMetadata(
            duration_ms=round(float(duration) * 1000),
            width=int(video_stream["width"]),
            height=int(video_stream["height"]),
            video_codec=str(video_stream["codec_name"]),
            has_audio=any(
                stream.get("codec_type") == "audio" for stream in data["streams"]
            ),
        )
    except (subprocess.SubprocessError, json.JSONDecodeError, KeyError, StopIteration, ValueError) as exc:
        raise AppError("INVALID_VIDEO", "无法读取视频，请检查文件是否完整。") from exc


def validate_media(
    path: Path,
    size_bytes: int,
    duration_ms: int,
    max_upload_bytes: int,
    min_duration_seconds: int,
    max_duration_seconds: int,
) -> None:
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise AppError("UNSUPPORTED_FORMAT", "仅支持 MP4、MOV 和 WebM 视频。")
    if size_bytes > max_upload_bytes:
        raise AppError("FILE_TOO_LARGE", "视频大小不能超过 300 MB。")
    if duration_ms < min_duration_seconds * 1000:
        raise AppError("VIDEO_TOO_SHORT", f"视频不能短于 {min_duration_seconds} 秒。")
    if duration_ms > max_duration_seconds * 1000:
        raise AppError("VIDEO_TOO_LONG", f"视频不能超过 {max_duration_seconds // 60} 分钟。")
