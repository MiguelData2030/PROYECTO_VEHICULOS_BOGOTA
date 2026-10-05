"""
init_db.py — creates all database tables for AutoNegocio.

Run from the project root:
    python -m database.init_db
or:
    python database/init_db.py

The SQLite file (autonegocio.db) will be created in the current working
directory (project root).
"""

import asyncio
import sys
import os

# Allow running as a script from the project root without installing the package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.models.database import engine, Base

# Import every model so SQLAlchemy registers them on the Base metadata.
from backend.models.vehiculo import Vehiculo          # noqa: F401
from backend.models.cliente import Cliente            # noqa: F401
from backend.models.transaccion import Transaccion    # noqa: F401
from backend.models.precio_mercado import PrecioMercado  # noqa: F401
from backend.models.oportunidad import Oportunidad    # noqa: F401


async def init_db() -> None:
    """Drop-and-recreate strategy (dev). Switch to checkfirst=True for prod."""
    async with engine.begin() as conn:
        # create_all is idempotent when tables already exist (checkfirst=True default).
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully.")
    print(f"Tables: {', '.join(Base.metadata.tables.keys())}")


async def drop_all() -> None:
    """Utility: drop every table (use with caution in production)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("All tables dropped.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AutoNegocio DB initializer")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all tables before creating them (destructive!)",
    )
    args = parser.parse_args()

    async def run() -> None:
        if args.drop:
            confirm = input("This will DELETE all data. Type 'yes' to continue: ")
            if confirm.strip().lower() != "yes":
                print("Aborted.")
                return
            await drop_all()
        await init_db()

    asyncio.run(run())
