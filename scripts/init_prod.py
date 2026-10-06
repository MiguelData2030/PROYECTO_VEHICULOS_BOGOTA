"""
One-time production setup against Supabase.

Fill `.env.prod` (git-ignored) and run from the project root:

    python -m scripts.init_prod

It is idempotent: running it again does nothing harmful.
  1. Creates all tables in the Supabase Postgres database.
  2. Creates the public Storage bucket for vehicle photos.
  3. Creates the admin user (scripts/create_admin.py).
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import prod_env

prod_env.load()  # must run before importing backend settings
_missing = prod_env.missing(["DATABASE_URL", "ADMIN_PASSWORD"])
if _missing:
    sys.exit(f"Faltan en .env.prod: {', '.join(_missing)}")

import httpx  # noqa: E402

from backend.config.settings import settings  # noqa: E402
from backend.models.database import Base, engine  # noqa: E402
from backend.services import storage  # noqa: E402
from scripts import create_admin  # noqa: E402


async def create_tables() -> None:
    import backend.models  # noqa: F401  (register models)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print(f"✓ Tablas listas: {', '.join(sorted(Base.metadata.tables))}")


async def create_bucket() -> None:
    if not (settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY):
        print("! SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY no definidas: se omite el bucket de fotos")
        return
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    headers = storage.auth_headers(key)
    base = settings.SUPABASE_URL.rstrip("/")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{base}/storage/v1/bucket/{settings.SUPABASE_BUCKET}", headers=headers)
        if r.status_code == 200:
            print(f"✓ Bucket '{settings.SUPABASE_BUCKET}' ya existe")
            return
        r = await client.post(
            f"{base}/storage/v1/bucket",
            headers=headers,
            json={
                "id": settings.SUPABASE_BUCKET,
                "name": settings.SUPABASE_BUCKET,
                "public": True,
                "file_size_limit": 4 * 1024 * 1024,
                "allowed_mime_types": ["image/jpeg", "image/png", "image/webp"],
            },
        )
        r.raise_for_status()
        print(f"✓ Bucket público '{settings.SUPABASE_BUCKET}' creado")


async def main() -> None:
    if settings.DATABASE_URL.startswith("sqlite"):
        sys.exit("DATABASE_URL apunta a SQLite. Define la URL de Supabase antes de ejecutar este script.")
    await create_tables()
    await create_bucket()
    await create_admin.create()  # also disposes the engine


if __name__ == "__main__":
    asyncio.run(main())
