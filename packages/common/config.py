from typing import Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    APP_NAME: str = "Codenter AI SDR Platform"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Database
    # Supports postgresql+asyncpg://sdr_admin:sdr_secret_password@localhost:5432/codenter_sdr
    # or sqlite+aiosqlite for local in-memory testing
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://sdr_admin:sdr_secret_password@localhost:5432/codenter_sdr"
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: Any) -> str:
        if isinstance(v, str):
            clean_v = v.strip()
            if clean_v.startswith("postgres://"):
                return clean_v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif clean_v.startswith("postgresql://") and not clean_v.startswith("postgresql+asyncpg://"):
                return clean_v.replace("postgresql://", "postgresql+asyncpg://", 1)
            return clean_v
        return v

    # Redis & Celery
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2")

    # Security & Auth
    JWT_SECRET: str = Field(default="dev-jwt-insecure-secret-key-change-in-prod-xyz-987")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENCRYPTION_KEY_SECRET: str = Field(
        default="k9_F_8a9B_3zQ2x1W_7vP0m5L4j3H2g1S0d9F8a7B6c="
    )

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            v_str = v.strip()
            if v_str.startswith("[") and v_str.endswith("]"):
                import json
                try:
                    return json.loads(v_str)
                except Exception:
                    pass
            return [orig.strip() for orig in v_str.split(",") if orig.strip()]
        return v

settings = Settings()
