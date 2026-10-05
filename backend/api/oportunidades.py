"""
Router: /oportunidades
Endpoints for vehicle buying opportunities identified by scrapers/agents.
Sorted by score descending by default.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.database import get_db
from backend.models import Oportunidad

router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class OportunidadBase(BaseModel):
    # Vehicle info from the listing
    marca: str = Field(..., max_length=50)
    modelo: str = Field(..., max_length=100)
    anio: int = Field(..., ge=1990, le=2030)
    tipo: Optional[str] = Field(None, max_length=50)
    version: Optional[str] = Field(None, max_length=100)
    kilometraje: Optional[int] = Field(None, ge=0)
    color: Optional[str] = Field(None, max_length=50)
    transmision: Optional[str] = Field(None, max_length=30)
    combustible: Optional[str] = Field(None, max_length=30)

    # Listing details
    precio_publicado: Decimal = Field(..., ge=0, description="Precio publicado en COP")
    precio_mercado_estimado: Optional[Decimal] = Field(None, ge=0, description="Precio de mercado estimado en COP")
    precio_venta_estimado: Optional[Decimal] = Field(None, ge=0, description="Precio de venta estimado en COP")
    descuento_vs_mercado_pct: Optional[float] = Field(None, description="% de descuento vs mercado (positivo = oferta)")
    margen_estimado_cop: Optional[Decimal] = Field(None, description="Margen bruto estimado en COP")
    margen_estimado_pct: Optional[float] = Field(None, description="Margen estimado en %")
    score: float = Field(0.0, ge=0.0, le=100.0, description="Score de oportunidad 0-100")

    # Provenance
    fuente: Optional[str] = Field(None, max_length=100, description="OLX, TuCarro, Mercadolibre, etc.")
    url: Optional[str] = Field(None, max_length=500)
    vendedor_nombre: Optional[str] = Field(None, max_length=150)
    vendedor_telefono: Optional[str] = Field(None, max_length=20)
    ubicacion: Optional[str] = Field(None, max_length=200, description="Ciudad/barrio del vendedor")

    # Status tracking
    estado: str = Field(
        "nueva",
        description="nueva | contactada | negociando | comprada | descartada | expirada",
    )
    notas: Optional[str] = None
    prioridad: str = Field("media", description="alta | media | baja")
    razon_score: Optional[str] = Field(None, description="Explicación del score generada por IA")


class OportunidadCreate(OportunidadBase):
    pass


class OportunidadEstadoUpdate(BaseModel):
    estado: str = Field(..., description="nueva | contactada | negociando | comprada | descartada | expirada")
    notas: Optional[str] = None

    def validate_estado(self) -> "OportunidadEstadoUpdate":
        opciones = {"nueva", "contactada", "negociando", "comprada", "descartada", "expirada"}
        if self.estado not in opciones:
            raise ValueError(f"estado debe ser uno de: {opciones}")
        return self


class OportunidadOut(OportunidadBase):
    id: int
    creado_en: Optional[datetime] = None
    actualizado_en: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OportunidadEstadisticas(BaseModel):
    total: int
    por_estado: dict[str, int]
    por_fuente: dict[str, int]
    por_marca: dict[str, int]
    score_promedio: Optional[float]
    margen_promedio_cop: Optional[Decimal]
    margen_promedio_pct: Optional[float]
    oportunidades_hoy: int
    top_marca: Optional[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/estadisticas", response_model=OportunidadEstadisticas, summary="Estadísticas de oportunidades")
async def estadisticas(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Oportunidad))
    opps: list[Oportunidad] = result.scalars().all()

    today = datetime.utcnow().date()
    total = len(opps)
    por_estado: dict[str, int] = {}
    por_fuente: dict[str, int] = {}
    por_marca: dict[str, int] = {}
    scores: list[float] = []
    margenes_cop: list[Decimal] = []
    margenes_pct: list[float] = []
    opp_hoy = 0

    for o in opps:
        por_estado[o.estado] = por_estado.get(o.estado, 0) + 1
        if o.fuente:
            por_fuente[o.fuente] = por_fuente.get(o.fuente, 0) + 1
        por_marca[o.marca] = por_marca.get(o.marca, 0) + 1
        scores.append(float(o.score))
        if o.margen_estimado_cop is not None:
            margenes_cop.append(Decimal(str(o.margen_estimado_cop)))
        if o.margen_estimado_pct is not None:
            margenes_pct.append(float(o.margen_estimado_pct))
        creado = o.creado_en
        if creado:
            creado_date = creado.date() if isinstance(creado, datetime) else creado
            if creado_date == today:
                opp_hoy += 1

    top_marca = max(por_marca, key=por_marca.get) if por_marca else None

    return OportunidadEstadisticas(
        total=total,
        por_estado=por_estado,
        por_fuente=por_fuente,
        por_marca=por_marca,
        score_promedio=sum(scores) / len(scores) if scores else None,
        margen_promedio_cop=sum(margenes_cop) / len(margenes_cop) if margenes_cop else None,
        margen_promedio_pct=sum(margenes_pct) / len(margenes_pct) if margenes_pct else None,
        oportunidades_hoy=opp_hoy,
        top_marca=top_marca,
    )


@router.get("/top", response_model=list[OportunidadOut], summary="Top 10 mejores oportunidades")
async def top_oportunidades(
    estado: str = Query("nueva", description="Filtrar por estado"),
    db: AsyncSession = Depends(get_db),
):
    """Returns the 10 highest-scored active opportunities."""
    result = await db.execute(
        select(Oportunidad)
        .where(Oportunidad.estado == estado)
        .order_by(desc(Oportunidad.score))
        .limit(10)
    )
    return result.scalars().all()


@router.get("", response_model=list[OportunidadOut], summary="Listar oportunidades")
async def listar_oportunidades(
    estado: Optional[str] = Query(None),
    fuente: Optional[str] = Query(None),
    marca: Optional[str] = Query(None),
    prioridad: Optional[str] = Query(None),
    score_min: Optional[float] = Query(None, ge=0, le=100),
    precio_max: Optional[Decimal] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """List all opportunities sorted by score descending."""
    conditions = []
    if estado:
        conditions.append(Oportunidad.estado == estado)
    if fuente:
        conditions.append(Oportunidad.fuente == fuente)
    if marca:
        from sqlalchemy import func
        conditions.append(func.lower(Oportunidad.marca) == marca.lower())
    if prioridad:
        conditions.append(Oportunidad.prioridad == prioridad)
    if score_min is not None:
        conditions.append(Oportunidad.score >= score_min)
    if precio_max is not None:
        conditions.append(Oportunidad.precio_publicado <= precio_max)

    stmt = select(Oportunidad)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(desc(Oportunidad.score)).offset(skip).limit(limit)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{oportunidad_id}", response_model=OportunidadOut, summary="Obtener oportunidad por ID")
async def obtener_oportunidad(oportunidad_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Oportunidad).where(Oportunidad.id == oportunidad_id))
    o = result.scalar_one_or_none()
    if not o:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oportunidad no encontrada")
    return o


@router.put("/{oportunidad_id}/estado", response_model=OportunidadOut, summary="Actualizar estado de oportunidad")
async def actualizar_estado(
    oportunidad_id: int,
    payload: OportunidadEstadoUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Lightweight status update. Typical flow:
    nueva → contactada → negociando → comprada | descartada
    """
    opciones = {"nueva", "contactada", "negociando", "comprada", "descartada", "expirada"}
    if payload.estado not in opciones:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"estado debe ser uno de: {opciones}",
        )

    result = await db.execute(select(Oportunidad).where(Oportunidad.id == oportunidad_id))
    o = result.scalar_one_or_none()
    if not o:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oportunidad no encontrada")

    o.estado = payload.estado
    if payload.notas:
        o.notas = (o.notas or "") + f"\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] {payload.notas}"

    await db.flush()
    await db.refresh(o)
    return o


@router.post("", response_model=OportunidadOut, status_code=status.HTTP_201_CREATED, summary="Crear oportunidad")
async def crear_oportunidad(payload: OportunidadCreate, db: AsyncSession = Depends(get_db)):
    o = Oportunidad(**payload.model_dump())
    db.add(o)
    await db.flush()
    await db.refresh(o)
    return o


@router.delete("/{oportunidad_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar oportunidad")
async def eliminar_oportunidad(oportunidad_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Oportunidad).where(Oportunidad.id == oportunidad_id))
    o = result.scalar_one_or_none()
    if not o:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oportunidad no encontrada")
    await db.delete(o)
