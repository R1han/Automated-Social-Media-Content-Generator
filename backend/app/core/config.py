"""Application configuration management."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Centralized application settings.

    Values are read from environment variables with sensible defaults so the demo
    can run locally without additional configuration. Secrets (e.g., API keys)
    should be injected via a real `.env` file that mirrors `.env.example`.
    """

    app_name: str = Field(default="Agent SM Backend")
    backend_cors_origins: str = Field(default="http://localhost:5173")

    gemini_api_key: str | None = Field(default=None, env="GEMINI_API_KEY")
    tts_api_key: str | None = Field(default=None, env="TTS_API_KEY")
    tts_voice_id: str = Field(default="JBFqnCBsd6RMkjVDRZzb", env="TTS_VOICE_ID")
    tts_model: str = Field(default="eleven_multilingual_v2", env="TTS_MODEL")

    assets_dir: str = Field(default=str(BACKEND_ROOT / "assets"))
    outputs_dir: str = Field(default=str(BACKEND_ROOT / "outputs"))

    primary_color: str = Field(default="#300A55")
    secondary_color: str = Field(default="#EBEDFA")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance for app-wide reuse."""

    return Settings()  # type: ignore[call-arg]
