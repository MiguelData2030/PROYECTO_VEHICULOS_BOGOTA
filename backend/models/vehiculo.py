"""
Vehiculo model — represents a car in inventory (bought, being sold, or tracked).
All monetary values are in Colombian Pesos (COP).
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Boolean, DateTime, Float, Index, Integer, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .database import Base


class Vehiculo(Base):
    __tablename__ = "vehiculos"

    # --- Primary key ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # --- Identification ---
    marca: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    modelo: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    año: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    placa: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)

    # --- Pricing (COP) ---
    precio_compra: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    precio_venta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    precio_mercado: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # --- Technical specs ---
    kilometraje: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    transmision: Mapped[str] = mapped_column(String(20), nullable=False)       # automatica / mecanica
    combustible: Mapped[str] = mapped_column(String(20), nullable=False)       # gasolina / diesel / hibrido / electrico
    color: Mapped[str] = mapped_column(String(50), nullable=False)
    cilindraje: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # cc
    num_dueños: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tipo_vehiculo: Mapped[str] = mapped_column(String(30), nullable=False)     # SUV / Sedan / Hatchback / Camioneta / Pick-up

    # --- Location ---
    ciudad: Mapped[str] = mapped_column(String(100), nullable=False, default="Bogotá")

    # --- Status ---
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="disponible"
    )  # disponible / vendido / en_proceso / reservado
    estado_mecanico: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # excelente / bueno / regular

    # --- Documentation flags ---
    soat_vigente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tecnicomecanica_vigente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    impuestos_al_dia: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    libre_prendas: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # --- Description & media ---
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fotos: Mapped[Optional[List]] = mapped_column(JSON, nullable=True)         # list of photo URLs

    # --- Source / origin ---
    fuente: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # tucarro / carroya / particular / subasta
    url_fuente: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # --- Business intelligence ---
    margen_estimado: Mapped[Optional[float]] = mapped_column(Float, nullable=True)   # %
    score_oportunidad: Mapped[Optional[float]] = mapped_column(Float, nullable=True) # 0-100

    # --- Key dates ---
    fecha_compra: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_venta: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_publicacion: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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
        "Transaccion", back_populates="vehiculo", cascade="all, delete-orphan"
    )

    # --- Composite indexes ---
    __table_args__ = (
        Index("ix_vehiculos_marca_modelo_año", "marca", "modelo", "año"),
    )

    def __repr__(self) -> str:
        return f"<Vehiculo {self.año} {self.marca} {self.modelo} | {self.estado}>"
