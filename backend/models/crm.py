"""
CRM models — sales pipeline follow-up and social media performance.

New tables only (create_all adds them on startup; existing tables untouched).
`demo` marks rows created by the demo generator so they can be removed.
"""

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

ETAPAS = ("nuevo", "contactado", "cita", "negociacion", "ganado", "perdido")
CANALES = ("instagram", "facebook", "tiktok", "whatsapp", "web", "tucarro", "referido", "vitrina")
TIPOS_INTERACCION = ("llamada", "whatsapp", "mensaje_red", "email", "visita", "test_drive", "cotizacion", "nota")
REDES = ("instagram", "facebook", "tiktok", "whatsapp")


class Seguimiento(Base):
    """One sales opportunity with a client (a deal in the pipeline)."""

    __tablename__ = "crm_seguimientos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_id: Mapped[int] = mapped_column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False, index=True)
    vehiculo_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("vehiculos.id", ondelete="SET NULL"), nullable=True)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, default="compra")  # compra (cliente compra) | venta (nos vende)
    etapa: Mapped[str] = mapped_column(String(20), nullable=False, default="nuevo", index=True)
    canal: Mapped[str] = mapped_column(String(20), nullable=False, default="web", index=True)
    valor_estimado: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    probabilidad: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-100
    proxima_accion: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    fecha_proxima: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    responsable: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    motivo_perdida: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    interacciones: Mapped[List["Interaccion"]] = relationship(
        back_populates="seguimiento", cascade="all, delete-orphan", order_by="Interaccion.fecha"
    )


class Interaccion(Base):
    """A touchpoint with the client: call, WhatsApp, DM, visit, test drive…"""

    __tablename__ = "crm_interacciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    seguimiento_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("crm_seguimientos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    resumen: Mapped[str] = mapped_column(Text, nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    seguimiento: Mapped[Seguimiento] = relationship(back_populates="interacciones")


class RedMetrica(Base):
    """Daily metrics of one social network account."""

    __tablename__ = "redes_metricas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    red: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    seguidores: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    alcance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    interacciones: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mensajes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    leads: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inversion: Mapped[float] = mapped_column(Float, nullable=False, default=0)  # paid ads (COP)
    demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)


class Publicacion(Base):
    """A social media post and its results."""

    __tablename__ = "redes_publicaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    red: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # reel | carrusel | historia | video | post
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    vehiculo_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("vehiculos.id", ondelete="SET NULL"), nullable=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    alcance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    me_gusta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comentarios: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    compartidos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    guardados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mensajes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    leads: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imagen: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
