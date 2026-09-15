"""Application settings loaded from environment."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration from .env and environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_chat_model: str = Field(
        default="gpt-4.1",
        alias="OPENAI_CHAT_MODEL",
    )
    default_timezone: str = Field(
        default="Europe/Berlin",
        alias="DEFAULT_TIMEZONE",
    )
    default_reminder_time: str = Field(
        default="09:00",
        alias="DEFAULT_REMINDER_TIME",
    )
    sqlite_path: str = Field(
        default="./data/notes.db",
        alias="SQLITE_PATH",
    )
    scheduler_interval_seconds: int = Field(
        default=15,
        alias="SCHEDULER_INTERVAL_SECONDS",
    )
    stuck_processing_minutes: int = Field(
        default=5,
        alias="STUCK_PROCESSING_MINUTES",
    )
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
