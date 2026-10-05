"""
Create a default admin user for development.
Run: python -m scripts.create_admin
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from passlib.context import CryptContext
from backend.models.database import engine, Base, AsyncSessionLocal
from backend.models.usuario import Usuario
from sqlalchemy import select

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

USERNAME = "admin"
EMAIL = "admin@autonegocio.co"
PASSWORD = "admin123"


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
        print(f"Admin user created: {USERNAME} / {PASSWORD}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create())
