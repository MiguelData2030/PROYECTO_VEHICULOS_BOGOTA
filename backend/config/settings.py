from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AutoNegocio API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database — SQLite for dev, PostgreSQL for production
    # Set DATABASE_URL env var in production (e.g. postgresql+asyncpg://user:pass@host/db)
    DATABASE_URL: str = "sqlite+aiosqlite:///./autonegocio.db"

    # JWT Auth
    SECRET_KEY: str = "autonegocio-secret-key-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Scraping
    SCRAPING_INTERVAL_MINUTES: int = 30
    MAX_CONCURRENT_SCRAPERS: int = 5
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # Claude AI
    ANTHROPIC_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"

    # Business Rules
    MIN_MARGIN_PERCENT: float = 10.0
    MAX_VEHICLE_AGE_YEARS: int = 15
    MAX_KM_PER_YEAR: int = 20000
    TARGET_BRANDS: list = [
        "Toyota", "Mazda", "Chevrolet", "Kia", "Renault",
        "Hyundai", "Nissan", "Ford", "Volkswagen", "Suzuki"
    ]
    PRIORITY_SEGMENTS: list = ["SUV", "Camioneta", "Sedan"]

    class Config:
        env_file = ".env"


settings = Settings()
