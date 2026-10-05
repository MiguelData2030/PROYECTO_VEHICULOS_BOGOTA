"""
Photo storage for vehicle images.

- Production: Supabase Storage (public bucket). Enabled when SUPABASE_URL and
  SUPABASE_SERVICE_ROLE_KEY are set. Returns absolute public URLs.
- Development: local ./uploads folder served by FastAPI at /uploads.
  Returns relative URLs (/uploads/...).
"""

from __future__ import annotations

import os

import httpx

from backend.config.settings import settings

CONTENT_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


def using_supabase() -> bool:
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY)


def _base() -> str:
    return settings.SUPABASE_URL.rstrip("/")


def _headers() -> dict:
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    return {"Authorization": f"Bearer {key}", "apikey": key}


def _public_prefix() -> str:
    return f"{_base()}/storage/v1/object/public/{settings.SUPABASE_BUCKET}/"


async def save_photo(path: str, data: bytes, ext: str) -> str:
    """Store `data` at `path` (e.g. 'vehiculos/3/abc.jpg') and return its public URL."""
    if using_supabase():
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{_base()}/storage/v1/object/{settings.SUPABASE_BUCKET}/{path}",
                content=data,
                headers={
                    **_headers(),
                    "Content-Type": CONTENT_TYPES.get(ext, "application/octet-stream"),
                    "x-upsert": "true",
                },
            )
            r.raise_for_status()
        return _public_prefix() + path

    local_path = os.path.join("uploads", *path.split("/"))
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    with open(local_path, "wb") as fh:
        fh.write(data)
    return f"/uploads/{path}"


async def delete_photo(url: str, expected_prefix: str) -> None:
    """
    Delete a photo previously returned by save_photo.

    Only files under `expected_prefix` (e.g. 'vehiculos/3/') are touched, so a
    URL pointing elsewhere is just unlinked from the vehicle, never deleted.
    """
    if url.startswith(_public_prefix() if using_supabase() else "/uploads/"):
        path = url.split("/uploads/", 1)[-1] if not using_supabase() else url[len(_public_prefix()):]
        if not path.startswith(expected_prefix) or ".." in path:
            return
        if using_supabase():
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.request(
                    "DELETE",
                    f"{_base()}/storage/v1/object/{settings.SUPABASE_BUCKET}",
                    json={"prefixes": [path]},
                    headers=_headers(),
                )
                r.raise_for_status()
        else:
            local_path = os.path.join("uploads", *path.split("/"))
            if os.path.isfile(local_path):
                os.remove(local_path)
