from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "local"

    DATABASE_URL: str = "postgresql+asyncpg://social:social@db:5432/social"
    TEST_DATABASE_URL: str = "postgresql+asyncpg://social:social@db:5432/social_test"
    REDIS_URL: str = "redis://redis:6379/0"

    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
