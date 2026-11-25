"""Configuración de la aplicación (variables de entorno / archivo .env)."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Banco E6 · Procesamiento de Transacciones Bancarias"
    APP_VERSION: str = "1.0.0"
    APP_ENV: Literal["development", "test", "production"] = "development"
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = Field(..., description="postgresql+asyncpg://usuario:contraseña@host:5432/base")
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False

    ZONA_HORARIA: str = "America/Hermosillo"
    CORS_ORIGINS: Annotated[list[str], NoDecode] = []

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _separar_origenes(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def _exigir_asyncpg(cls, v: str) -> str:
        if v.startswith("postgresql://") or v.startswith("postgres://"):
            v = "postgresql+asyncpg://" + v.split("://", 1)[1]
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL debe usar el driver postgresql+asyncpg")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
