"""
Router: /oportunidades
Endpoints for vehicle buying opportunities identified by scrapers/agents.
Sorted by score descending by default.
"""

from __future__ import annotations

from datetime import datetime, timezone
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

ESTADOS_OPORTUNIDAD = {"nueva", "contactada", "negociando", "comprada", "descartada", "expirada"}


class OportunidadBase(BaseModel):
    """Mirrors backend.models.oportunidad.Oportunidad."""
    url: str = Field(..., max_length=1000)
    plataforma: str = Field(..., max_length=30, description="tucarro | carroya | olx | facebook | manual")
    marca: str = Field(..., max_length=100)
    modelo: str = Field(..., max_length=100)
    año: int = Field(..., ge=1990, le=2030)
    kilometraje: Optional[int] = Field(None, ge=0)
    ubicacion: Optional[str] = Field(None, max_length=200)
    precio_publicado: float = Field(..., ge=0, description="Precio publicado en COP")
    precio_mercado_estimado: Optional[float] = Field(None, ge=0, description="Precio de mercado estimado en COP")
    descuento_porcentaje: Optional[float] = Field(None, description="% bajo el mercado (positivo = oferta)")
    score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Score de oportunidad 0-100")
    descripcion_corta: Optional[str] = None
    estado: str = Field("nueva", description="nueva | contactada | negociando | comprada | descartada | expirada")
    notas: Optional[str] = None


class OportunidadCreate(OportunidadBase):
    pass


class OportunidadEstadoUpdate(BaseModel):
    estado: str = Field(..., description="nueva | contactada | negociando | comprada | descartada | expirada")
    notas: Optional[str] = None


class OportunidadOut(OportunidadBase):
    id: int
    detectada_en: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OportunidadEstadisticas(BaseModel):
    total: int
    por_estado: dict[str, int]
    por_plataforma: dict[str, int]
    por_marca: dict[str, int]
    score_promedio: Optional[float]
    descuento_promedio_pct: Optional[float]
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
    por_estado: dict[str, int] = {}
    por_plataforma: dict[str, int] = {}
    por_marca: dict[str, int] = {}
    scores: list[float] = []
    descuentos: list[float] = []
    opp_hoy = 0

    for o in opps:
        por_estado[o.estado] = por_estado.get(o.estado, 0) + 1
        por_plataforma[o.plataforma] = por_plataforma.get(o.plataforma, 0) + 1
        por_marca[o.marca] = por_marca.get(o.marca, 0) + 1
        if o.score is not None:
            scores.append(float(o.score))
        if o.descuento_porcentaje is not None:
            descuentos.append(float(o.descuento_porcentaje))
        if o.detectada_en and o.detectada_en.date() == today:
            opp_hoy += 1

    return OportunidadEstadisticas(
        total=len(opps),
        por_estado=por_estado,
        por_plataforma=por_plataforma,
        por_marca=por_marca,
        score_promedio=sum(scores) / len(scores) if scores else None,
        descuento_promedio_pct=sum(descuentos) / len(descuentos) if descuentos else None,
        oportunidades_hoy=opp_hoy,
        top_marca=max(por_marca, key=por_marca.get) if por_marca else None,
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
    plataforma: Optional[str] = Query(None),
    marca: Optional[str] = Query(None),
    score_min: Optional[float] = Query(None, ge=0, le=100),
    precio_max: Optional[float] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """List all opportunities sorted by score descending."""
    conditions = []
    if estado:
        conditions.append(Oportunidad.estado == estado)
    if plataforma:
        conditions.append(Oportunidad.plataforma == plataforma)
    if marca:
        from sqlalchemy import func
        conditions.append(func.lower(Oportunidad.marca) == marca.lower())
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
    if payload.estado not in ESTADOS_OPORTUNIDAD:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"estado debe ser uno de: {ESTADOS_OPORTUNIDAD}",
        )

    result = await db.execute(select(Oportunidad).where(Oportunidad.id == oportunidad_id))
    o = result.scalar_one_or_none()
    if not o:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oportunidad no encontrada")

    o.estado = payload.estado
    if payload.notas:
        stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        o.notas = f"{o.notas or ''}\n[{stamp}] {payload.notas}".strip()

    await db.flush()
    await db.refresh(o)
    return o


@router.post("", response_model=OportunidadOut, status_code=status.HTTP_201_CREATED, summary="Crear oportunidad")
async def crear_oportunidad(payload: OportunidadCreate, db: AsyncSession = Depends(get_db)):
    dup = await db.execute(select(Oportunidad).where(Oportunidad.url == payload.url))
    if dup.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una oportunidad con esa URL",
        )
    o = Oportunidad(**payload.model_dump(), detectada_en=datetime.now(tz=timezone.utc))
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
