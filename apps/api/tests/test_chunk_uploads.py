from pathlib import Path

import pytest

from app.errors import AppError
from app.services.chunk_uploads import assemble_chunks, create_session, load_manifest, write_chunk


def test_chunk_session_writes_and_assembles_in_order(tmp_path: Path) -> None:
    manifest = create_session(tmp_path, "lesson.mp4", "video/mp4", 10, 4, 3)
    assert load_manifest(tmp_path, manifest.upload_id) == manifest
    write_chunk(tmp_path, manifest, 0, b"abcd")
    write_chunk(tmp_path, manifest, 1, b"efgh")
    write_chunk(tmp_path, manifest, 2, b"ij")
    assert assemble_chunks(tmp_path, manifest).read_bytes() == b"abcdefghij"


def test_chunk_session_rejects_wrong_size_and_missing_parts(tmp_path: Path) -> None:
    manifest = create_session(tmp_path, "lesson.mp4", "video/mp4", 10, 4, 3)
    with pytest.raises(AppError):
        write_chunk(tmp_path, manifest, 0, b"bad")
    write_chunk(tmp_path, manifest, 0, b"abcd")
    with pytest.raises(AppError):
        assemble_chunks(tmp_path, manifest)
