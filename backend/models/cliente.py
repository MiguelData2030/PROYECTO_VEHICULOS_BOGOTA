"""
Cliente model — buyer, seller, or both.
All monetary values are in Colombian Pesos (COP).
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    # --- Primary key ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # --- Personal info ---
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    telefono: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    cedula: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, unique=True)

    # --- Role ---
    tipo: Mapped[str] = mapped_column(
        String(20), nullable=False, default="comprador"
    )  # comprador / vendedor / ambos

    # --- Interest & budget (COP) ---
    vehiculos_interes: Mapped[Optional[List]] = mapped_column(JSON, nullable=True)  # list of search criteria dicts
    presupuesto_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    presupuesto_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # --- Notes ---
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Audit timestamps ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now()
    )

    # --- Relationships ---
    transacciones: Mapped[List["Transaccion"]] = relationship(  # noqa: F821
        "Transaccion", back_populates="cliente", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Cliente {self.nombre} ({self.tipo})>"
