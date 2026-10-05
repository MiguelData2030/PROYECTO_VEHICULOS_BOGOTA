"""
Oportunidad model — a buying opportunity detected by scrapers/agents.
All monetary values are in Colombian Pesos (COP).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Oportunidad(Base):
    __tablename__ = "oportunidades"

    # --- Primary key ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # --- Source ---
    url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    plataforma: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # tucarro / carroya / olx / facebook

    # --- Vehicle info ---
    marca: Mapped[str] = mapped_column(String(100), nullable=False)
    modelo: Mapped[str] = mapped_column(String(100), nullable=False)
    año: Mapped[int] = mapped_column(Integer, nullable=False)
    kilometraje: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ubicacion: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # --- Pricing (COP) ---
    precio_publicado: Mapped[float] = mapped_column(Float, nullable=False)
    precio_mercado_estimado: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    descuento_porcentaje: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # %

    # --- Scoring ---
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100

    # --- Description ---
    descripcion_corta: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Workflow state ---
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="nueva"
    )  # nueva / contactada / descartada / comprada
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Dates ---
    detectada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # --- Indexes ---
    __table_args__ = (
        Index("ix_oportunidades_marca_modelo_año", "marca", "modelo", "año"),
        Index("ix_oportunidades_score", "score"),
        Index("ix_oportunidades_estado", "estado"),
    )

    def __repr__(self) -> str:
        return (
            f"<Oportunidad {self.año} {self.marca} {self.modelo} "
            f"score={self.score} estado={self.estado}>"
        )
