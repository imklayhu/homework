from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = PROJECT_ROOT / "data"
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'app.db'}"
    cors_origin: str = "http://localhost:3000"

    on_demand_api_key: SecretStr | None = None
    on_demand_base_url: str | None = None
    bailian_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("BAILIAN_API_KEY", "API_KEY"),
    )
    bailian_base_url: str | None = None

    video_understanding_model: str = "qwen3-vl-flash"
    fallback_video_model: str = "qwen3-vl-plus"
    transcription_model: str = "qwen3-asr-flash-2026-02-10"
    enable_asr: bool = False
    demo_mode: bool = False

    max_upload_bytes: int = 300 * 1024 * 1024
    min_duration_seconds: int = 180
    max_duration_seconds: int = 900

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def remixes_dir(self) -> Path:
        return self.data_dir / "remixes"

    @property
    def temp_dir(self) -> Path:
        return self.data_dir / "tmp"

    def ensure_directories(self) -> None:
        for directory in (self.uploads_dir, self.remixes_dir, self.temp_dir):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
