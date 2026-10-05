"""
Transaccion model — records each buy/sell transaction.
All monetary values are in Colombian Pesos (COP).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Transaccion(Base):
    __tablename__ = "transacciones"

    # --- Primary key ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # --- Foreign keys ---
    vehiculo_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vehiculos.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    cliente_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # --- Transaction details ---
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)  # compra / venta

    # --- Financials (COP) ---
    precio: Mapped[float] = mapped_column(Float, nullable=False)
    comision: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gastos_traspaso: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gastos_reacondicionamiento: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ganancia_neta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # --- Date & notes ---
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Audit timestamp ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # --- Relationships ---
    vehiculo: Mapped["Vehiculo"] = relationship(  # noqa: F821
        "Vehiculo", back_populates="transacciones"
    )
    cliente: Mapped["Cliente"] = relationship(  # noqa: F821
        "Cliente", back_populates="transacciones"
    )

    def __repr__(self) -> str:
        return (
            f"<Transaccion {self.tipo} vehiculo_id={self.vehiculo_id} "
            f"precio={self.precio:,.0f} COP>"
        )
