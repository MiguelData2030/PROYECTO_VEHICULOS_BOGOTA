"""
SQLAlchemy async engine, session factory, Base class, and get_db dependency.

Database:
- Development: SQLite via aiosqlite (autonegocio.db in project root).
- Production: Supabase PostgreSQL via asyncpg. DATABASE_URL may be pasted
  exactly as Supabase shows it (postgresql://...); it is normalised here.
"""

import os
import uuid
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from backend.config.settings import settings


def _build_engine_args(url: str) -> tuple[str, dict]:
    """Return (sqlalchemy_url, engine_kwargs) for the configured database."""
    if url.startswith("sqlite"):
        return url, {}

    # postgres:// or postgresql:// → postgresql+asyncpg://
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+asyncpg://" + url[len(prefix):]
            break

    # asyncpg does not understand libpq's ?sslmode=...; Supabase always needs TLS.
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k not in ("sslmode", "pgbouncer")]
    # SQLAlchemy-level cache of prepared statements (dialect option, set via URL)
    query.append(("prepared_statement_cache_size", "0"))
    url = urlunsplit(parts._replace(query=urlencode(query)))

    kwargs: dict = {
        "connect_args": {
            "ssl": "require",
            # Supabase's pooler (Supavisor, port 6543) runs in transaction mode,
            # which does not support prepared statements.
            "statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4().hex}__",
        },
        "pool_pre_ping": True,
    }
    # Serverless (Vercel): each invocation may run in a fresh instance, so
    # don't keep connections open between requests — the pooler does that.
    if os.environ.get("VERCEL"):
        kwargs["poolclass"] = NullPool
    return url, kwargs


_url, _engine_kwargs = _build_engine_args(settings.DATABASE_URL)

engine = create_async_engine(_url, echo=False, future=True, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all models."""
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
