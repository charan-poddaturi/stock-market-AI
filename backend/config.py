from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # App
    app_name: str = "StockAI Platform"
    app_version: str = "1.0.0"
    environment: str = "development"
    secret_key: str = "supersecretchangeme"
    debug: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://stockai:stockai_secret@localhost:5432/stockai"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # API Keys
    alpha_vantage_key: Optional[str] = "demo"
    polygon_key: Optional[str] = "demo"
    news_api_key: Optional[str] = "demo"
    gemini_api_key: Optional[str] = "AIzaSyCKcZ8YWlvJoOzh6kBUbHMWmisdYdX3BxU"

    # ML Settings
    model_cache_dir: str = "models/saved"
    default_lookback_days: int = 252
    sequence_length: int = 60
    prediction_horizons: list = [1, 7, 30]

    # CORS
    cors_origins: list = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
