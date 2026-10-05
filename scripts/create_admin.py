"""
Create the admin user.
Run: python -m scripts.create_admin

Credentials come from ADMIN_USERNAME / ADMIN_EMAIL / ADMIN_PASSWORD env vars.
Without ADMIN_PASSWORD a random password is generated and printed once.
"""
import asyncio
import secrets
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from passlib.context import CryptContext
from backend.models.database import engine, Base, AsyncSessionLocal
from backend.models.usuario import Usuario
from sqlalchemy import select

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
EMAIL = os.environ.get("ADMIN_EMAIL", "admin@autonegocio.co")
PASSWORD_FROM_ENV = bool(os.environ.get("ADMIN_PASSWORD"))
PASSWORD = os.environ.get("ADMIN_PASSWORD") or secrets.token_urlsafe(12)


async def create():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Usuario).where(Usuario.username == USERNAME))
        if result.scalar_one_or_none():
            print(f"Admin user '{USERNAME}' already exists.")
            return

        user = Usuario(
            username=USERNAME,
            email=EMAIL,
            hashed_password=pwd_context.hash(PASSWORD),
            is_admin=True,
        )
        session.add(user)
        await session.commit()
        if PASSWORD_FROM_ENV:
            print(f"Admin user created: {USERNAME} (password from ADMIN_PASSWORD)")
        else:
            print(f"Admin user created: {USERNAME} / {PASSWORD}  <- guárdala, no se volverá a mostrar")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create())
