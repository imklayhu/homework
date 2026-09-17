from pathlib import Path

import pytest

from app.errors import AppError
from app.services.media import probe_video, validate_media


FIXTURE = Path(__file__).parent / "fixtures" / "sample.mp4"


def test_probe_video_returns_video_and_audio_metadata() -> None:
    metadata = probe_video(FIXTURE)

    assert 3_900 <= metadata.duration_ms <= 4_100
    assert metadata.width == 640
    assert metadata.height == 360
    assert metadata.video_codec == "h264"
    assert metadata.has_audio is True


def test_validate_media_rejects_unsupported_extension() -> None:
    with pytest.raises(AppError, match="UNSUPPORTED_FORMAT"):
        validate_media(Path("lesson.exe"), 10, 4_000, 100, 1, 10)


def test_validate_media_rejects_file_over_limit() -> None:
    with pytest.raises(AppError, match="FILE_TOO_LARGE"):
        validate_media(Path("lesson.mp4"), 101, 4_000, 100, 1, 10)


def test_validate_media_rejects_duration_outside_limits() -> None:
    with pytest.raises(AppError, match="VIDEO_TOO_SHORT"):
        validate_media(Path("lesson.mp4"), 10, 500, 100, 1, 10)

    with pytest.raises(AppError, match="VIDEO_TOO_LONG"):
        validate_media(Path("lesson.mp4"), 10, 11_000, 100, 1, 10)
