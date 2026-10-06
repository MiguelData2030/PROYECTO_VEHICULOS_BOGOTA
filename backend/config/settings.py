from pydantic_settings import BaseSettings
from typing import Optional
import hashlib
import hmac
import os


DEFAULT_SECRET_KEY = "autonegocio-secret-key-change-in-production-2026"


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AutoNegocio API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database — SQLite for dev, PostgreSQL for production
    # Set DATABASE_URL env var in production (e.g. postgresql+asyncpg://user:pass@host/db)
    DATABASE_URL: str = "sqlite+aiosqlite:///./autonegocio.db"

    # JWT Auth
    SECRET_KEY: str = DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # CORS — comma-separated list of allowed origins.
    # In production set e.g. CORS_ORIGINS=https://www.autonegocio.co,https://autonegocio.vercel.app
    CORS_ORIGINS: str = "*"

    # Supabase Storage (vehicle photos). Leave empty in development to store
    # photos in ./uploads instead.
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_BUCKET: str = "fotos"

    # Vercel Cron sends "Authorization: Bearer <CRON_SECRET>" to /scraping/cron
    CRON_SECRET: Optional[str] = None

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


def _apply_supabase_integration(s: Settings) -> Settings:
    """
    Use the variables injected by the Supabase ↔ Vercel integration, so no
    secret has to be copied by hand:
      POSTGRES_URL           → DATABASE_URL
      SUPABASE_SECRET_KEY    → SUPABASE_SERVICE_ROLE_KEY (newer integration name)
      SUPABASE_JWT_SECRET    → derives a stable SECRET_KEY for our own JWTs
    Explicitly set variables always win.
    """
    if not os.environ.get("DATABASE_URL") and os.environ.get("POSTGRES_URL"):
        s.DATABASE_URL = os.environ["POSTGRES_URL"]
    if not s.SUPABASE_SERVICE_ROLE_KEY and os.environ.get("SUPABASE_SECRET_KEY"):
        s.SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SECRET_KEY"]
    if not s.SUPABASE_URL and os.environ.get("NEXT_PUBLIC_SUPABASE_URL"):
        s.SUPABASE_URL = os.environ["NEXT_PUBLIC_SUPABASE_URL"]
    jwt_secret = os.environ.get("SUPABASE_JWT_SECRET")
    if s.SECRET_KEY == DEFAULT_SECRET_KEY and jwt_secret:
        s.SECRET_KEY = hmac.new(jwt_secret.encode(), b"autonegocio-api-jwt", hashlib.sha256).hexdigest()
    # On Vercel we are always in production
    if os.environ.get("VERCEL") and "DEBUG" not in os.environ:
        s.DEBUG = False
    return s


settings = _apply_supabase_integration(Settings())
