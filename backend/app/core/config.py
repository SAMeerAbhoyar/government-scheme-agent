import os
from typing import List, Union, Any
from pydantic import AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Automated Government Scheme Recommendation Agent"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SQL_ECHO: bool = False

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./scheme_agent.db"
    DATABASE_URL_SYNC: str = "sqlite:///./scheme_agent.db"

    # JWT Security
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Column Encryption Key
    ENCRYPTION_KEY: str = ""

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # AI Placeholders
    EMBEDDING_DIMENSION: int = 768
    EMBEDDING_MODEL: str = "text-embedding-004"
    LLM_PROVIDER: str = "gemini"
    LLM_API_KEY: str = "placeholder"

    # Maintenance & Notifications
    MAX_CONSECUTIVE_FETCH_FAILURES: int = 3
    SEND_EMAIL_NOTIFICATIONS: bool = False
    ENABLE_INGESTION_SCHEDULER: bool = False
    RATE_LIMIT_PER_MINUTE: int = 60

    @model_validator(mode="before")
    @classmethod
    def fallback_profile_encryption_key(cls, data: Any) -> Any:
        if isinstance(data, dict):
            db_url = str(data.get("DATABASE_URL") or "")
            if "postgresql" in db_url:
                data["DATABASE_URL"] = "sqlite+aiosqlite:///./scheme_agent.db"
            db_sync_url = str(data.get("DATABASE_URL_SYNC") or "")
            if "postgresql" in db_sync_url:
                data["DATABASE_URL_SYNC"] = "sqlite:///./scheme_agent.db"
            if not data.get("ENCRYPTION_KEY") and data.get("PROFILE_ENCRYPTION_KEY"):
                data["ENCRYPTION_KEY"] = data["PROFILE_ENCRYPTION_KEY"]
        return data

    @model_validator(mode="after")
    def validate_secrets_and_encryption_key(self):
        if self.ENVIRONMENT.lower() != "testing":
            if not self.JWT_SECRET_KEY or len(self.JWT_SECRET_KEY.strip()) < 32:
                raise ValueError("JWT_SECRET_KEY is required and must be at least 32 characters long.")
            if not self.ENCRYPTION_KEY or len(self.ENCRYPTION_KEY.strip()) < 32:
                raise ValueError("ENCRYPTION_KEY is required and must be at least 32 characters long.")
        return self

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
