"""
Router: /agentes
AI Agent endpoints for vehicle hunting and valuation.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ValuacionRequest(BaseModel):
    marca: str = Field(..., examples=["Toyota"])
    modelo: str = Field(..., examples=["Corolla"])
    año: int = Field(..., ge=1990, le=2030, examples=[2023])
    kilometraje: int = Field(..., ge=0, examples=[25000])
    transmision: str = Field("automatica", examples=["automatica"])
    combustible: str = Field("gasolina", examples=["gasolina"])
    color: str = Field("blanco", examples=["blanco"])
    tipo_vehiculo: str = Field("SUV", examples=["SUV"])
    ciudad: str = Field("Bogotá", examples=["Bogotá"])
    estado_mecanico: str = Field("bueno", examples=["bueno"])


class ValuacionResponse(BaseModel):
    precio_mercado_estimado: Optional[int] = None
    precio_compra_sugerido: Optional[int] = None
    precio_venta_sugerido: Optional[int] = None
    margen_estimado_pct: Optional[float] = None
    score: float
    analisis: str
    datos_mercado: dict


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/valuar",
    response_model=ValuacionResponse,
    summary="Valuar un vehículo con IA",
)
async def valuar_vehiculo(payload: ValuacionRequest):
    """
    Use the Agente Valuador to estimate market value, suggest buy/sell prices,
    and generate an analysis. Uses Claude API when available, falls back to
    algorithmic valuation.
    """
    from backend.agents.valuador import AgenteValuador

    valuador = AgenteValuador()
    result = await valuador.valuate(
        marca=payload.marca,
        modelo=payload.modelo,
        año=payload.año,
        kilometraje=payload.kilometraje,
        transmision=payload.transmision,
        combustible=payload.combustible,
        color=payload.color,
        tipo_vehiculo=payload.tipo_vehiculo,
        ciudad=payload.ciudad,
        estado_mecanico=payload.estado_mecanico,
    )
    return result


@router.post(
    "/cazar",
    summary="Ejecutar el Agente Cazador",
)
async def ejecutar_cazador(
    marca: Optional[str] = Query(None, description="Filtrar por marca"),
    precio_max: Optional[float] = Query(None, description="Precio máximo"),
    max_pages: int = Query(2, ge=1, le=10, description="Páginas por plataforma"),
):
    """
    Run the Agente Cazador to scrape platforms, score listings, and return
    a prioritized alert with top opportunities.
    """
    from backend.agents.cazador import AgenteCazador

    filters = {"max_pages": max_pages}
    if marca:
        filters["marca"] = marca
    if precio_max:
        filters["precio_max"] = precio_max

    cazador = AgenteCazador(filters=filters)
    alerta = await cazador.run_and_alert()

    return {"alerta": alerta}
