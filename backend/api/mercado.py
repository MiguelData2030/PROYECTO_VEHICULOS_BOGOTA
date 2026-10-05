"""
Router: /mercado
Market data endpoints: average prices, trends, and vehicle comparison.
Uses the PrecioMercado model populated by scrapers/agents.
All prices in COP.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.database import get_db
from backend.models import PrecioMercado, Vehiculo

router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class PrecioMercadoOut(BaseModel):
    marca: str
    modelo: str
    anio: int
    tipo: Optional[str] = None
    transmision: Optional[str] = None
    combustible: Optional[str] = None
    precio_promedio: Decimal
    precio_minimo: Decimal
    precio_maximo: Decimal
    mediana: Optional[Decimal] = None
    cantidad_muestras: int
    fuente: Optional[str] = None
    fecha_actualizacion: Optional[date] = None

    model_config = {"from_attributes": True}


class TendenciaPunto(BaseModel):
    fecha: date
    precio_promedio: Decimal
    cantidad_muestras: int


class TendenciaResponse(BaseModel):
    marca: str
    modelo: str
    anio: int
    puntos: list[TendenciaPunto]
    variacion_pct: Optional[float] = Field(
        None, description="Variación % del precio desde el primer al último punto"
    )


class ComparacionResponse(BaseModel):
    vehiculo_id: int
    marca: str
    modelo: str
    anio: int
    kilometraje: int
    precio_venta_cop: Decimal

    # Market reference
    precio_mercado_promedio: Optional[Decimal]
    precio_mercado_minimo: Optional[Decimal]
    precio_mercado_maximo: Optional[Decimal]
    cantidad_muestras_mercado: int

    # Analysis
    diferencia_vs_mercado_cop: Optional[Decimal] = Field(
        None, description="precio_venta - precio_mercado_promedio (negativo = por debajo del mercado)"
    )
    diferencia_vs_mercado_pct: Optional[float] = Field(
        None, description="% diferencia vs mercado (negativo = oportunidad de compra)"
    )
    evaluacion: Optional[str] = Field(
        None,
        description="muy_economico | economico | precio_mercado | caro | muy_caro",
    )
    muestras: Optional[list[dict]] = Field(None, description="Lista de precios similares en el mercado")


# ---------------------------------------------------------------------------
# Helper: categorize a price relative to market
# ---------------------------------------------------------------------------

def _evaluar_precio(precio: Decimal, promedio: Decimal, std_pct: float = 15.0) -> str:
    """
    Classify how a price compares to the market average.
    Thresholds based on percentage deviation:
      < -20% → muy_economico
      -20% to -5% → economico
      -5% to +5% → precio_mercado
      +5% to +20% → caro
      > +20% → muy_caro
    """
    if promedio == 0:
        return "sin_referencia"
    diff_pct = float((precio - promedio) / promedio * 100)
    if diff_pct < -20:
        return "muy_economico"
    if diff_pct < -5:
        return "economico"
    if diff_pct <= 5:
        return "precio_mercado"
    if diff_pct <= 20:
        return "caro"
    return "muy_caro"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/precios", response_model=list[PrecioMercadoOut], summary="Precios promedio de mercado")
async def precios_mercado(
    marca: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    anio: Optional[int] = Query(None),
    anio_min: Optional[int] = Query(None),
    anio_max: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None),
    transmision: Optional[str] = Query(None),
    fuente: Optional[str] = Query(None),
    dias_vigencia: int = Query(
        90, ge=1, le=365,
        description="Solo incluir registros actualizados en los últimos N días",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns average market prices per brand/model/year combination.
    Optionally filter by brand, model, year range, type, transmission, source.
    Results are limited to records updated within the last `dias_vigencia` days.
    """
    cutoff = date.today() - timedelta(days=dias_vigencia)
    conditions = [PrecioMercado.fecha_actualizacion >= cutoff]

    if marca:
        conditions.append(func.lower(PrecioMercado.marca) == marca.lower())
    if modelo:
        conditions.append(func.lower(PrecioMercado.modelo) == modelo.lower())
    if anio:
        conditions.append(PrecioMercado.anio == anio)
    if anio_min:
        conditions.append(PrecioMercado.anio >= anio_min)
    if anio_max:
        conditions.append(PrecioMercado.anio <= anio_max)
    if tipo:
        conditions.append(func.lower(PrecioMercado.tipo) == tipo.lower())
    if transmision:
        conditions.append(func.lower(PrecioMercado.transmision) == transmision.lower())
    if fuente:
        conditions.append(PrecioMercado.fuente == fuente)

    stmt = (
        select(PrecioMercado)
        .where(and_(*conditions))
        .order_by(PrecioMercado.marca, PrecioMercado.modelo, desc(PrecioMercado.anio))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/tendencias", response_model=TendenciaResponse, summary="Tendencia de precios en el tiempo")
async def tendencias(
    marca: str = Query(..., description="Marca del vehículo, ej: Toyota"),
    modelo: str = Query(..., description="Modelo, ej: Corolla"),
    anio: int = Query(..., ge=1990, le=2030),
    dias: int = Query(180, ge=30, le=730, description="Ventana de tiempo en días"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns time-series price data for a specific make/model/year,
    grouped by week. Useful for plotting price trend charts.
    """
    cutoff = date.today() - timedelta(days=dias)

    stmt = (
        select(PrecioMercado)
        .where(
            and_(
                func.lower(PrecioMercado.marca) == marca.lower(),
                func.lower(PrecioMercado.modelo) == modelo.lower(),
                PrecioMercado.anio == anio,
                PrecioMercado.fecha_actualizacion >= cutoff,
            )
        )
        .order_by(PrecioMercado.fecha_actualizacion)
    )
    result = await db.execute(stmt)
    registros: list[PrecioMercado] = result.scalars().all()

    if not registros:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No hay datos de mercado para {marca} {modelo} {anio}",
        )

    puntos: list[TendenciaPunto] = [
        TendenciaPunto(
            fecha=r.fecha_actualizacion,
            precio_promedio=Decimal(str(r.precio_promedio)),
            cantidad_muestras=r.cantidad_muestras,
        )
        for r in registros
    ]

    # Calculate price variation
    variacion_pct: Optional[float] = None
    if len(puntos) >= 2:
        p_inicio = puntos[0].precio_promedio
        p_fin = puntos[-1].precio_promedio
        if p_inicio > 0:
            variacion_pct = float((p_fin - p_inicio) / p_inicio * 100)

    return TendenciaResponse(
        marca=marca,
        modelo=modelo,
        anio=anio,
        puntos=puntos,
        variacion_pct=variacion_pct,
    )


@router.get("/comparar", response_model=ComparacionResponse, summary="Comparar precio de vehículo vs mercado")
async def comparar_precio(
    vehiculo_id: int = Query(..., description="ID del vehículo en inventario"),
    dias_vigencia: int = Query(90, ge=1, le=365),
    incluir_muestras: bool = Query(False, description="Incluir lista de precios similares"),
    db: AsyncSession = Depends(get_db),
):
    """
    Compares the sale price of a vehicle in inventory against current
    market data for the same make/model/year. Returns the evaluation:
    muy_economico | economico | precio_mercado | caro | muy_caro.
    """
    # Fetch vehicle
    v_result = await db.execute(select(Vehiculo).where(Vehiculo.id == vehiculo_id))
    vehiculo = v_result.scalar_one_or_none()
    if not vehiculo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado")

    # Find market data for this vehicle
    cutoff = date.today() - timedelta(days=dias_vigencia)
    stmt = (
        select(PrecioMercado)
        .where(
            and_(
                func.lower(PrecioMercado.marca) == vehiculo.marca.lower(),
                func.lower(PrecioMercado.modelo) == vehiculo.modelo.lower(),
                PrecioMercado.anio == vehiculo.anio,
                PrecioMercado.fecha_actualizacion >= cutoff,
            )
        )
        .order_by(desc(PrecioMercado.fecha_actualizacion))
    )
    result = await db.execute(stmt)
    registros: list[PrecioMercado] = result.scalars().all()

    precio_venta = Decimal(str(vehiculo.precio_venta))

    if not registros:
        return ComparacionResponse(
            vehiculo_id=vehiculo.id,
            marca=vehiculo.marca,
            modelo=vehiculo.modelo,
            anio=vehiculo.anio,
            kilometraje=vehiculo.kilometraje,
            precio_venta_cop=precio_venta,
            precio_mercado_promedio=None,
            precio_mercado_minimo=None,
            precio_mercado_maximo=None,
            cantidad_muestras_mercado=0,
            diferencia_vs_mercado_cop=None,
            diferencia_vs_mercado_pct=None,
            evaluacion="sin_datos_mercado",
        )

    # Aggregate market data from all records found
    promedios = [Decimal(str(r.precio_promedio)) for r in registros]
    minimos = [Decimal(str(r.precio_minimo)) for r in registros]
    maximos = [Decimal(str(r.precio_maximo)) for r in registros]
    total_muestras = sum(r.cantidad_muestras for r in registros)

    promedio_mercado = sum(promedios) / len(promedios)
    minimo_mercado = min(minimos)
    maximo_mercado = max(maximos)

    diferencia_cop = precio_venta - promedio_mercado
    diferencia_pct = float(diferencia_cop / promedio_mercado * 100) if promedio_mercado > 0 else None

    evaluacion = _evaluar_precio(precio_venta, promedio_mercado)

    muestras_list: Optional[list[dict]] = None
    if incluir_muestras:
        muestras_list = [
            {
                "fuente": r.fuente,
                "fecha": str(r.fecha_actualizacion),
                "precio_promedio": float(r.precio_promedio),
                "precio_minimo": float(r.precio_minimo),
                "precio_maximo": float(r.precio_maximo),
                "cantidad_muestras": r.cantidad_muestras,
            }
            for r in registros
        ]

    return ComparacionResponse(
        vehiculo_id=vehiculo.id,
        marca=vehiculo.marca,
        modelo=vehiculo.modelo,
        anio=vehiculo.anio,
        kilometraje=vehiculo.kilometraje,
        precio_venta_cop=precio_venta,
        precio_mercado_promedio=promedio_mercado,
        precio_mercado_minimo=minimo_mercado,
        precio_mercado_maximo=maximo_mercado,
        cantidad_muestras_mercado=total_muestras,
        diferencia_vs_mercado_cop=diferencia_cop,
        diferencia_vs_mercado_pct=diferencia_pct,
        evaluacion=evaluacion,
        muestras=muestras_list,
    )


@router.get("/resumen", summary="Resumen del mercado por segmento")
async def resumen_mercado(
    dias_vigencia: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """
    High-level market summary: cheapest and most expensive segments,
    most active brands, and data freshness.
    """
    cutoff = date.today() - timedelta(days=dias_vigencia)
    stmt = select(PrecioMercado).where(PrecioMercado.fecha_actualizacion >= cutoff)
    result = await db.execute(stmt)
    registros: list[PrecioMercado] = result.scalars().all()

    if not registros:
        return {"mensaje": "No hay datos de mercado disponibles", "total_registros": 0}

    por_marca: dict[str, list[float]] = {}
    por_tipo: dict[str, list[float]] = {}
    total_muestras = 0

    for r in registros:
        precio = float(r.precio_promedio)
        por_marca.setdefault(r.marca, []).append(precio)
        if r.tipo:
            por_tipo.setdefault(r.tipo, []).append(precio)
        total_muestras += r.cantidad_muestras

    marcas_resumen = {
        marca: {
            "precio_promedio_cop": round(sum(precios) / len(precios)),
            "registros": len(precios),
        }
        for marca, precios in sorted(por_marca.items())
    }

    tipos_resumen = {
        tipo: {
            "precio_promedio_cop": round(sum(precios) / len(precios)),
            "registros": len(precios),
        }
        for tipo, precios in sorted(por_tipo.items())
    }

    return {
        "total_registros": len(registros),
        "total_muestras": total_muestras,
        "dias_vigencia": dias_vigencia,
        "fecha_mas_reciente": str(max(r.fecha_actualizacion for r in registros)),
        "fecha_mas_antigua": str(min(r.fecha_actualizacion for r in registros)),
        "por_marca": marcas_resumen,
        "por_tipo": tipos_resumen,
    }
