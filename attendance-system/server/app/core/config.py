"""
Core configuration loaded from environment variables / .env file.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── Database ──
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/attendance_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Auth ──
    SECRET_KEY: str = "change-me-to-a-random-64-char-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── Reader API keys ──
    READER_API_KEYS: str = ""  # comma-separated

    # ── Session defaults ──
    DEFAULT_FRESHNESS_DELTA_SEC: int = 120
    DEFAULT_MIN_PRESENCE_PCT: int = 75

    # ── RFID tag map ──
    # Optional override for the known-tag map path. When empty, the server uses
    # its own project-local server/tag_map.json (see routers/rfid_scan.py).
    TAG_MAP_PATH: str = ""

    @property
    def reader_api_key_list(self) -> list[str]:
        return [k.strip() for k in self.READER_API_KEYS.split(",") if k.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
