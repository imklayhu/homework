from pathlib import Path

from app.models import Video
from tests.test_video_api import FIXTURE, make_client


def test_chunked_upload_creates_video_and_cleans_session(tmp_path: Path) -> None:
    client, session = make_client(tmp_path)
    content = FIXTURE.read_bytes()
    chunk_size = max(1, len(content) // 3)
    total_chunks = (len(content) + chunk_size - 1) // chunk_size
    initialized = client.post("/api/uploads/init", json={"filename": "lesson.mp4", "content_type": "video/mp4", "size_bytes": len(content), "chunk_size": chunk_size, "total_chunks": total_chunks})
    assert initialized.status_code == 201
    upload_id = initialized.json()["upload_id"]

    for index in range(total_chunks):
        chunk = content[index * chunk_size:(index + 1) * chunk_size]
        response = client.put(f"/api/uploads/{upload_id}/chunks/{index}", content=chunk, headers={"content-type": "application/octet-stream"})
        assert response.status_code == 204

    completed = client.post(f"/api/uploads/{upload_id}/complete")
    assert completed.status_code == 202
    video = session.get(Video, completed.json()["video_id"])
    assert video is not None
    assert (tmp_path / video.storage_key).read_bytes() == content
    assert not (tmp_path / "tmp" / "chunk-uploads" / upload_id).exists()


def test_chunked_upload_rejects_missing_and_bad_chunks(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)
    initialized = client.post("/api/uploads/init", json={"filename": "lesson.mp4", "content_type": "video/mp4", "size_bytes": 10, "chunk_size": 4, "total_chunks": 3})
    upload_id = initialized.json()["upload_id"]
    assert client.put(f"/api/uploads/{upload_id}/chunks/0", content=b"bad").status_code == 400
    assert client.put(f"/api/uploads/{upload_id}/chunks/0", content=b"abcd").status_code == 204
    assert client.post(f"/api/uploads/{upload_id}/complete").status_code == 409
