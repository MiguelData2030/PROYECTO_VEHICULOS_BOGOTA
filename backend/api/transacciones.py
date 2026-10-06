"""
Router: /transacciones
Buy / sell transactions and the business KPIs derived from them.
All amounts in COP. Mirrors backend.models.transaccion.Transaccion.

ganancia_neta (sales only) = precio de venta
                             - precio de compra del vehículo
                             - comisión - gastos de traspaso - reacondicionamiento
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Cliente, Transaccion, Vehiculo
from backend.models.database import get_db

router = APIRouter()

TIPOS = {"compra", "venta"}

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class TransaccionCreate(BaseModel):
    vehiculo_id: int
    cliente_id: int
    tipo: str = Field(..., description="compra | venta")
    precio: float = Field(..., gt=0, description="Precio de la transacción en COP")
    comision: Optional[float] = Field(None, ge=0)
    gastos_traspaso: Optional[float] = Field(None, ge=0, description="Traspaso, notaría, RUNT")
    gastos_reacondicionamiento: Optional[float] = Field(None, ge=0, description="Taller, pintura, llantas, lavado")
    fecha: date = Field(default_factory=date.today)
    notas: Optional[str] = None

    @field_validator("tipo")
    @classmethod
    def tipo_valido(cls, v: str) -> str:
        if v not in TIPOS:
            raise ValueError(f"tipo debe ser uno de: {sorted(TIPOS)}")
        return v


class TransaccionOut(BaseModel):
    id: int
    vehiculo_id: int
    cliente_id: int
    tipo: str
    precio: float
    comision: Optional[float] = None
    gastos_traspaso: Optional[float] = None
    gastos_reacondicionamiento: Optional[float] = None
    ganancia_neta: Optional[float] = None
    margen_pct: Optional[float] = None
    fecha: datetime
    notas: Optional[str] = None
    vehiculo_nombre: Optional[str] = None
    cliente_nombre: Optional[str] = None
    dias_en_inventario: Optional[int] = None


class MesKPI(BaseModel):
    mes: str  # YYYY-MM
    ventas: int
    ingresos: float
    ganancia: float
    compras: int
    inversion: float


class DashboardKPIs(BaseModel):
    ventas_mes_actual: int
    ingresos_mes_actual: float
    ganancia_mes_actual: float
    ventas_12m: int
    ingresos_12m: float
    ganancia_12m: float
    margen_promedio_pct: Optional[float]
    ticket_promedio: Optional[float]
    dias_promedio_venta: Optional[float]
    vehiculos_en_inventario: int
    valor_inventario_venta: float
    capital_invertido: float
    meses: list[MesKPI]
    ventas_por_marca: dict[str, int]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _as_date(value) -> Optional[date]:
    if value is None:
        return None
    return value.date() if isinstance(value, datetime) else value


def _gastos(tx: Transaccion) -> float:
    return (tx.comision or 0) + (tx.gastos_traspaso or 0) + (tx.gastos_reacondicionamiento or 0)


def _ganancia(tx: Transaccion, vehiculo: Optional[Vehiculo]) -> Optional[float]:
    if tx.tipo != "venta" or not vehiculo or not vehiculo.precio_compra:
        return None
    return tx.precio - vehiculo.precio_compra - _gastos(tx)


def _to_out(tx: Transaccion, vehiculo: Optional[Vehiculo], cliente: Optional[Cliente]) -> dict:
    ganancia = tx.ganancia_neta if tx.ganancia_neta is not None else _ganancia(tx, vehiculo)
    margen = None
    if ganancia is not None and vehiculo and vehiculo.precio_compra:
        margen = round(ganancia / vehiculo.precio_compra * 100, 1)
    dias = None
    if tx.tipo == "venta" and vehiculo and vehiculo.fecha_compra:
        dias = (_as_date(tx.fecha) - _as_date(vehiculo.fecha_compra)).days
    return {
        "id": tx.id,
        "vehiculo_id": tx.vehiculo_id,
        "cliente_id": tx.cliente_id,
        "tipo": tx.tipo,
        "precio": tx.precio,
        "comision": tx.comision,
        "gastos_traspaso": tx.gastos_traspaso,
        "gastos_reacondicionamiento": tx.gastos_reacondicionamiento,
        "ganancia_neta": ganancia,
        "margen_pct": margen,
        "fecha": tx.fecha,
        "notas": tx.notas,
        "vehiculo_nombre": f"{vehiculo.marca} {vehiculo.modelo} {vehiculo.año}" if vehiculo else None,
        "cliente_nombre": cliente.nombre if cliente else None,
        "dias_en_inventario": dias,
    }


def _month_key(d: date) -> str:
    return f"{d.year}-{d.month:02d}"


def _last_12_months(today: date) -> list[str]:
    keys = []
    y, m = today.year, today.month
    for _ in range(12):
        keys.append(f"{y}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(keys))


# ---------------------------------------------------------------------------
# Endpoints (fixed paths before /{id})
# ---------------------------------------------------------------------------


@router.get("/dashboard", response_model=DashboardKPIs, summary="KPIs del negocio")
async def dashboard(db: AsyncSession = Depends(get_db)):
    today = date.today()
    meses_keys = _last_12_months(today)
    meses = {k: {"ventas": 0, "ingresos": 0.0, "ganancia": 0.0, "compras": 0, "inversion": 0.0} for k in meses_keys}

    txs = (await db.execute(select(Transaccion))).scalars().all()
    vehiculos = {v.id: v for v in (await db.execute(select(Vehiculo))).scalars().all()}

    ventas_mes = 0
    ingresos_mes = ganancia_mes = 0.0
    margenes: list[float] = []
    tickets: list[float] = []
    dias_venta: list[int] = []
    por_marca: dict[str, int] = defaultdict(int)

    for tx in txs:
        d = _as_date(tx.fecha)
        key = _month_key(d)
        v = vehiculos.get(tx.vehiculo_id)
        if tx.tipo == "venta":
            g = tx.ganancia_neta if tx.ganancia_neta is not None else (_ganancia(tx, v) or 0.0)
            if key in meses:
                meses[key]["ventas"] += 1
                meses[key]["ingresos"] += tx.precio
                meses[key]["ganancia"] += g
                tickets.append(tx.precio)
                if v and v.precio_compra:
                    margenes.append(g / v.precio_compra * 100)
                if v and v.fecha_compra:
                    dias_venta.append((d - _as_date(v.fecha_compra)).days)
                if v:
                    por_marca[v.marca] += 1
            if key == meses_keys[-1]:
                ventas_mes += 1
                ingresos_mes += tx.precio
                ganancia_mes += g
        elif tx.tipo == "compra" and key in meses:
            meses[key]["compras"] += 1
            meses[key]["inversion"] += tx.precio + _gastos(tx)

    en_inventario = [v for v in vehiculos.values() if v.estado != "vendido"]
    return DashboardKPIs(
        ventas_mes_actual=ventas_mes,
        ingresos_mes_actual=ingresos_mes,
        ganancia_mes_actual=ganancia_mes,
        ventas_12m=sum(m["ventas"] for m in meses.values()),
        ingresos_12m=sum(m["ingresos"] for m in meses.values()),
        ganancia_12m=sum(m["ganancia"] for m in meses.values()),
        margen_promedio_pct=round(sum(margenes) / len(margenes), 1) if margenes else None,
        ticket_promedio=sum(tickets) / len(tickets) if tickets else None,
        dias_promedio_venta=round(sum(dias_venta) / len(dias_venta), 1) if dias_venta else None,
        vehiculos_en_inventario=len(en_inventario),
        valor_inventario_venta=sum(v.precio_venta or 0 for v in en_inventario),
        capital_invertido=sum(v.precio_compra or 0 for v in en_inventario),
        meses=[MesKPI(mes=k, **meses[k]) for k in meses_keys],
        ventas_por_marca=dict(sorted(por_marca.items(), key=lambda kv: -kv[1])),
    )


@router.get("", response_model=list[TransaccionOut], summary="Listar transacciones")
async def listar_transacciones(
    tipo: Optional[str] = Query(None, description="compra | venta"),
    vehiculo_id: Optional[int] = Query(None),
    cliente_id: Optional[int] = Query(None),
    desde: Optional[date] = Query(None),
    hasta: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    conditions = []
    if tipo:
        conditions.append(Transaccion.tipo == tipo)
    if vehiculo_id:
        conditions.append(Transaccion.vehiculo_id == vehiculo_id)
    if cliente_id:
        conditions.append(Transaccion.cliente_id == cliente_id)
    if desde:
        conditions.append(Transaccion.fecha >= datetime.combine(desde, time.min, tzinfo=timezone.utc))
    if hasta:
        conditions.append(Transaccion.fecha <= datetime.combine(hasta, time.max, tzinfo=timezone.utc))

    stmt = select(Transaccion)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(Transaccion.fecha.desc(), Transaccion.id.desc()).offset(skip).limit(limit)
    txs = (await db.execute(stmt)).scalars().all()
    if not txs:
        return []

    v_ids = {t.vehiculo_id for t in txs}
    c_ids = {t.cliente_id for t in txs}
    vehiculos = {v.id: v for v in (await db.execute(select(Vehiculo).where(Vehiculo.id.in_(v_ids)))).scalars().all()}
    clientes = {c.id: c for c in (await db.execute(select(Cliente).where(Cliente.id.in_(c_ids)))).scalars().all()}
    return [_to_out(t, vehiculos.get(t.vehiculo_id), clientes.get(t.cliente_id)) for t in txs]


@router.get("/{transaccion_id}", response_model=TransaccionOut, summary="Obtener transacción")
async def obtener_transaccion(transaccion_id: int, db: AsyncSession = Depends(get_db)):
    tx = await db.get(Transaccion, transaccion_id)
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transacción no encontrada")
    return _to_out(tx, await db.get(Vehiculo, tx.vehiculo_id), await db.get(Cliente, tx.cliente_id))


@router.post("", response_model=TransaccionOut, status_code=status.HTTP_201_CREATED, summary="Registrar compra o venta")
async def crear_transaccion(payload: TransaccionCreate, db: AsyncSession = Depends(get_db)):
    vehiculo = await db.get(Vehiculo, payload.vehiculo_id)
    if not vehiculo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado")
    cliente = await db.get(Cliente, payload.cliente_id)
    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    if payload.tipo == "venta" and vehiculo.estado == "vendido":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este vehículo ya está vendido")

    fecha = datetime.combine(payload.fecha, time(12, 0), tzinfo=timezone.utc)
    tx = Transaccion(**payload.model_dump(exclude={"fecha"}), fecha=fecha)

    # Keep the vehicle in sync with the transaction
    if payload.tipo == "venta":
        # Purchase-side costs (our own traspaso, reconditioning) also reduce the profit
        compras = (await db.execute(select(Transaccion).where(
            Transaccion.vehiculo_id == vehiculo.id, Transaccion.tipo == "compra"
        ))).scalars().all()
        ganancia = _ganancia(tx, vehiculo)
        tx.ganancia_neta = None if ganancia is None else ganancia - sum(_gastos(c) for c in compras)
        vehiculo.estado = "vendido"
        vehiculo.fecha_venta = fecha
        vehiculo.precio_venta = payload.precio
    else:
        vehiculo.estado = "disponible" if vehiculo.estado == "vendido" else vehiculo.estado
        vehiculo.fecha_compra = fecha
        vehiculo.precio_compra = payload.precio

    db.add(tx)
    await db.flush()
    await db.refresh(tx)
    return _to_out(tx, vehiculo, cliente)


@router.delete("/{transaccion_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Anular transacción")
async def eliminar_transaccion(transaccion_id: int, db: AsyncSession = Depends(get_db)):
    tx = await db.get(Transaccion, transaccion_id)
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transacción no encontrada")
    if tx.tipo == "venta":
        # Undo the sale: the vehicle goes back to stock
        vehiculo = await db.get(Vehiculo, tx.vehiculo_id)
        if vehiculo and vehiculo.estado == "vendido":
            vehiculo.estado = "disponible"
            vehiculo.fecha_venta = None
    await db.delete(tx)
