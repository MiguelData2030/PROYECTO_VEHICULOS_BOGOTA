"""
PrecioMercado model — historical market price snapshots for a make/model/year.
All monetary values are in Colombian Pesos (COP).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class PrecioMercado(Base):
    __tablename__ = "precios_mercado"

    # --- Primary key ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # --- Vehicle reference ---
    marca: Mapped[str] = mapped_column(String(100), nullable=False)
    modelo: Mapped[str] = mapped_column(String(100), nullable=False)
    año: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- Price stats (COP) ---
    precio_promedio: Mapped[float] = mapped_column(Float, nullable=False)
    precio_min: Mapped[float] = mapped_column(Float, nullable=False)
    precio_max: Mapped[float] = mapped_column(Float, nullable=False)
    num_muestras: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    kilometraje_promedio: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # --- Source metadata ---
    fuente: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # tucarro / carroya / olx / etc.
    ciudad: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # --- Dates ---
    fecha_consulta: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # --- Indexes ---
    __table_args__ = (
        Index("ix_precios_mercado_marca_modelo_año", "marca", "modelo", "año"),
        Index("ix_precios_mercado_fecha_consulta", "fecha_consulta"),
    )

    def __repr__(self) -> str:
        return (
            f"<PrecioMercado {self.año} {self.marca} {self.modelo} "
            f"avg={self.precio_promedio:,.0f} COP>"
        )
