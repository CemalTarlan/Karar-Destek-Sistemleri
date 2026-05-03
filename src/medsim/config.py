"""Application settings loaded from environment / .env file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the MedSim Triage system.

    All values can be overridden via environment variables or a local
    `.env` file. See `.env.example` for the full list.
    """

    lm_studio_base_url: str = Field(default="http://localhost:1234/v1")
    lm_studio_model: str = Field(default="local-model")
    lm_studio_timeout: int = Field(default=60, ge=1, le=600)

    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000, ge=1, le=65535)

    chroma_persist_dir: Path = Field(default=Path("./data/chroma"))

    log_level: str = Field(default="INFO")

    rules_path: Path = Field(
        default=Path(__file__).parent / "rules" / "data" / "triage_rules.yaml"
    )
    red_flags_path: Path = Field(
        default=Path(__file__).parent / "rules" / "data" / "red_flags.yaml"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached `Settings` instance."""
    return Settings()
