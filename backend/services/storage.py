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


def auth_headers(key: str) -> dict:
    """
    Supabase auth headers for a server-side key.

    New-style secret keys (sb_secret_...) are not JWTs: they go only in the
    `apikey` header and the API gateway authorises the request with them.
    Legacy service_role keys are JWTs and are also sent as a Bearer token.
    """
    if key.startswith("sb_"):
        return {"apikey": key}
    return {"Authorization": f"Bearer {key}", "apikey": key}


def _headers() -> dict:
    return auth_headers(settings.SUPABASE_SERVICE_ROLE_KEY)


def _public_prefix() -> str:
    return f"{_base()}/storage/v1/object/public/{settings.SUPABASE_BUCKET}/"


async def ensure_bucket(client: httpx.AsyncClient) -> None:
    """Create the public photos bucket if it does not exist yet."""
    r = await client.get(f"{_base()}/storage/v1/bucket/{settings.SUPABASE_BUCKET}", headers=_headers())
    if r.status_code == 200:
        return
    r = await client.post(
        f"{_base()}/storage/v1/bucket",
        headers=_headers(),
        json={
            "id": settings.SUPABASE_BUCKET,
            "name": settings.SUPABASE_BUCKET,
            "public": True,
            "file_size_limit": 4 * 1024 * 1024,
            "allowed_mime_types": list(set(CONTENT_TYPES.values())),
        },
    )
    if r.status_code not in (200, 201, 409):  # 409 = created concurrently
        r.raise_for_status()


async def save_photo(path: str, data: bytes, ext: str) -> str:
    """Store `data` at `path` (e.g. 'vehiculos/3/abc.jpg') and return its public URL."""
    if using_supabase():
        async with httpx.AsyncClient(timeout=60) as client:
            upload = lambda: client.post(  # noqa: E731
                f"{_base()}/storage/v1/object/{settings.SUPABASE_BUCKET}/{path}",
                content=data,
                headers={
                    **_headers(),
                    "Content-Type": CONTENT_TYPES.get(ext, "application/octet-stream"),
                    "x-upsert": "true",
                },
            )
            r = await upload()
            if r.status_code in (400, 404) and "not found" in r.text.lower():
                # First upload ever: create the public bucket, then retry
                await ensure_bucket(client)
                r = await upload()
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
