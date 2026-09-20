import os
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Automated Government Scheme Recommendation Agent"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    POSTGRES_USER: str = "scheme_user"
    POSTGRES_PASSWORD: str = "scheme_password"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "scheme_db"
    DATABASE_URL: str = "postgresql+asyncpg://scheme_user:scheme_password@localhost:5432/scheme_db"
    DATABASE_URL_SYNC: str = "postgresql+psycopg://scheme_user:scheme_password@localhost:5432/scheme_db"

    # JWT Security
    JWT_SECRET_KEY: str = "super-secret-jwt-key-change-this-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # CORS
    CORS_ORIGINS: List[str] = [
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
