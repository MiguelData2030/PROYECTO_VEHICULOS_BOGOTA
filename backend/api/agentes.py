"""
Router: /agentes (admin only)
AI agents: Valuador (pricing), Cazador (buying opportunities) and Marketing
(sales copy). All work without an API key; with ANTHROPIC_API_KEY they add a
written analysis by Claude.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.base_agent import ia_disponible
from backend.config.settings import settings
from backend.models import Vehiculo
from backend.models.database import get_db

router = APIRouter()


class ValuacionRequest(BaseModel):
    marca: str = Field(..., examples=["Mazda"])
    modelo: str = Field(..., examples=["CX-5"])
    año: int = Field(..., ge=1990, le=2030, examples=[2021])
    kilometraje: int = Field(..., ge=0, examples=[45000])
    transmision: str = Field("automatica")
    combustible: str = Field("gasolina")
    color: str = Field("blanco")
    tipo_vehiculo: str = Field("SUV")
    ciudad: str = Field("Bogotá")
    estado_mecanico: str = Field("bueno", description="excelente | bueno | regular")
    num_dueños: int = Field(1, ge=1)
    precio_pedido: Optional[float] = Field(None, ge=0, description="Lo que pide el vendedor (COP)")
    url_anuncio: Optional[str] = Field(None, description="Si se valúa un anuncio del mercado, se excluye de los comparables")


@router.get("/estado", summary="¿Está activa la IA de Claude?")
async def estado():
    return {
        "ia_activa": ia_disponible(),
        "modelo": settings.CLAUDE_MODEL if ia_disponible() else None,
        "agentes": ["valuador", "cazador", "marketing"],
    }


@router.post("/valuar", summary="Agente Valuador: precio justo, compra máxima y venta sugerida")
async def valuar(payload: ValuacionRequest):
    from backend.agents.valuador import AgenteValuador

    return await AgenteValuador().valuate(**payload.model_dump())


@router.post("/cazar", summary="Agente Cazador: mejores oportunidades de compra")
async def cazar(
    escanear: bool = Query(False, description="True = escanear TuCarro ahora (30-60 s); False = analizar lo ya recolectado"),
    marca: Optional[str] = Query(None),
    precio_max: Optional[float] = Query(None, ge=0),
    score_min: float = Query(60, ge=0, le=100),
    limite: int = Query(10, ge=1, le=30),
):
    from backend.agents.cazador import AgenteCazador

    filtros = {k: v for k, v in {"marca": marca, "precio_max": precio_max, "max_pages": 10}.items() if v}
    return await AgenteCazador(filters=filtros, min_score=score_min).analizar(escanear=escanear, limite=limite)


@router.post("/marketing/{vehiculo_id}", summary="Agente de Marketing: textos de venta de un vehículo")
async def marketing(vehiculo_id: int, db: AsyncSession = Depends(get_db)):
    from backend.agents.marketing import AgenteMarketing

    vehiculo = await db.get(Vehiculo, vehiculo_id)
    if not vehiculo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado")
    return await AgenteMarketing().redactar(vehiculo)
