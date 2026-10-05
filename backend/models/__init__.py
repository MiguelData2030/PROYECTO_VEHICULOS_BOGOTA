"""
AutoNegocio models package.
Imports all ORM models and re-exports them for convenience.
"""

from .database import Base, AsyncSessionLocal, engine, get_db
from .vehiculo import Vehiculo
from .cliente import Cliente
from .transaccion import Transaccion
from .precio_mercado import PrecioMercado
from .oportunidad import Oportunidad
from .usuario import Usuario

__all__ = [
    # Database core
    "Base",
    "AsyncSessionLocal",
    "engine",
    "get_db",
    # Models
    "Vehiculo",
    "Cliente",
    "Transaccion",
    "PrecioMercado",
    "Oportunidad",
    "Usuario",
]
