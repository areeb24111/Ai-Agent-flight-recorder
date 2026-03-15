from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    # Database URL. Set DATABASE_URL in env to override (e.g. Postgres: postgresql://user:pass@host/dbname).
    database_url: str = Field(default="sqlite:///./agent_recorder.db", validation_alias="DATABASE_URL")
    openai_api_key: str | None = None

    # If set, POST /api/v1/runs and POST /api/v1/simulations require X-API-Key header.
    # If unset, auth is disabled (dev only).
    api_key: str | None = Field(default=None, validation_alias="API_KEY")

    # Per-client per-minute limits for write endpoints (0 = unlimited).
    rate_limit_ingest_per_minute: int = Field(default=120, validation_alias="RATE_LIMIT_INGEST_PER_MINUTE")
    rate_limit_simulations_per_minute: int = Field(
        default=30, validation_alias="RATE_LIMIT_SIMULATIONS_PER_MINUTE"
    )

    # Comma-separated origins for CORS (e.g. https://myapp.fly.dev,https://dashboard.example.com).
    # If unset, defaults to localhost dev origins.
    cors_origins: str | None = Field(default=None, validation_alias="CORS_ORIGINS")

    # If set, serve frontend static files from this directory (e.g. ./static). Use for single-host deploy.
    static_dir: str | None = Field(default=None, validation_alias="STATIC_DIR")


settings = Settings()