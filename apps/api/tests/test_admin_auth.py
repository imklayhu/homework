from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.services.admin import hash_password


def test_authenticate_alias_creates_admin_session(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path,
        database_url="sqlite://",
        admin_username="framewise-demo",
        admin_password=hash_password("FramewiseDemo2026!"),
    )
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        response = TestClient(app).post(
            "/api/admin/authenticate",
            json={"username": "framewise-demo", "password": "FramewiseDemo2026!"},
        )
        assert response.status_code == 200
        assert "framewise_admin" in response.cookies
    finally:
        app.dependency_overrides.clear()
