from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    gemini_api_key: str
    primary_models: str = "gemini-3.8-flash,gemini-3.5-flash,gemini-3.5-flash-lite"
    crosscheck_models: str = "gemini-3.5-flash-lite,gemini-flash-lite-latest"
    embed_model: str = "gemini-embedding-2"
    judge_runs: int = 3
    max_concurrency: int = 8
    request_timeout_s: int = 120

    storage_dir: Path = BACKEND_DIR / "storage"

    @property
    def primary_chain(self) -> list[str]:
        return [m.strip() for m in self.primary_models.split(",") if m.strip()]

    @property
    def crosscheck_chain(self) -> list[str]:
        return [m.strip() for m in self.crosscheck_models.split(",") if m.strip()]


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.storage_dir.mkdir(parents=True, exist_ok=True)
    return s
