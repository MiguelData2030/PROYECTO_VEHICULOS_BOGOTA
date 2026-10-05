"""
Router: /transacciones
CRUD for Transaccion model + monthly/yearly report and dashboard KPIs.
All monetary values in COP.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import extract, func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.database import get_db
from backend.models import Transaccion, Vehiculo, Cliente

router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class TransaccionBase(BaseModel):
    vehiculo_id: int
    cliente_id: Optional[int] = None
    tipo: str = Field(..., description="compra | venta | consignacion")
    precio_acordado: Decimal = Field(..., ge=0, description="Precio de la transacción en COP")
    forma_pago: Optional[str] = Field(None, description="efectivo | transferencia | financiado | credito")
    fecha: date = Field(default_factory=date.today)
    gastos_transaccion: Optional[Decimal] = Field(None, ge=0, description="Notaría, traspaso, etc. en COP")
    gastos_reparacion_tx: Optional[Decimal] = Field(None, ge=0, description="Reparaciones cubiertas en esta tx")
    descuento: Optional[Decimal] = Field(None, ge=0, description="Descuento aplicado en COP")
    comision: Optional[Decimal] = Field(None, ge=0, description="Comisión de intermediario en COP")
    impuestos: Optional[Decimal] = Field(None, ge=0, description="Impuestos de la transacción en COP")
    notas: Optional[str] = None
    numero_documento: Optional[str] = Field(None, max_length=50, description="# contrato / factura")
    vendedor: Optional[str] = Field(None, max_length=100, description="Nombre del asesor/vendedor")


class TransaccionCreate(TransaccionBase):

    @model_validator(mode="after")
    def tipo_valido(self) -> "TransaccionCreate":
        opciones = {"compra", "venta", "consignacion"}
        if self.tipo not in opciones:
            raise ValueError(f"tipo debe ser uno de: {opciones}")
        return self


class TransaccionUpdate(BaseModel):
    cliente_id: Optional[int] = None
    tipo: Optional[str] = None
    precio_acordado: Optional[Decimal] = Field(None, ge=0)
    forma_pago: Optional[str] = None
    fecha: Optional[date] = None
    gastos_transaccion: Optional[Decimal] = Field(None, ge=0)
    gastos_reparacion_tx: Optional[Decimal] = Field(None, ge=0)
    descuento: Optional[Decimal] = Field(None, ge=0)
    comision: Optional[Decimal] = Field(None, ge=0)
    impuestos: Optional[Decimal] = Field(None, ge=0)
    notas: Optional[str] = None
    numero_documento: Optional[str] = None
    vendedor: Optional[str] = None


class TransaccionOut(TransaccionBase):
    id: int
    ganancia_neta: Optional[Decimal] = None
    margen_pct: Optional[float] = None
    creado_en: Optional[datetime] = None

    # Denormalized for convenience
    vehiculo_nombre: Optional[str] = None
    cliente_nombre: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Report / KPI schemas
# ---------------------------------------------------------------------------

class MesReporte(BaseModel):
    anio: int
    mes: int
    ventas: int
    compras: int
    ingresos_cop: Decimal
    gastos_cop: Decimal
    ganancia_neta_cop: Decimal
    margen_pct: Optional[float]
    ticket_promedio_cop: Optional[Decimal]


class ReporteResponse(BaseModel):
    periodo: str
    meses: list[MesReporte]
    totales: dict


class DashboardKPIs(BaseModel):
    # Sales this calendar month
    ventas_mes_actual: int
    ingresos_mes_actual: Decimal
    ganancia_mes_actual: Decimal
    margen_promedio_mes: Optional[float]

    # Sales this year
    ventas_anio_actual: int
    ingresos_anio_actual: Decimal
    ganancia_anio_actual: Decimal

    # Inventory
    vehiculos_disponibles: int
    valor_inventario_cop: Decimal
    dias_promedio_inventario: Optional[float]

    # Velocity
    tiempo_promedio_venta_dias: Optional[float]

    # Overall
    total_transacciones: int
    ticket_promedio_cop: Optional[Decimal]


# ---------------------------------------------------------------------------
# Helper: compute ganancia_neta for a venta transaction
# ---------------------------------------------------------------------------

def _calcular_ganancia(tx: Transaccion, precio_compra: Optional[Decimal]) -> Optional[Decimal]:
    """
    ganancia_neta = precio_acordado
                    - precio_compra (if available)
                    - gastos_transaccion
                    - gastos_reparacion_tx
                    - comision
                    - impuestos
                    + (no descuento subtracted here — descuento already reduces precio_acordado)
    """
    if tx.tipo != "venta":
        return None
    if precio_compra is None:
        return None

    ganancia = Decimal(str(tx.precio_acordado)) - Decimal(str(precio_compra))
    for field in ("gastos_transaccion", "gastos_reparacion_tx", "comision", "impuestos"):
        val = getattr(tx, field)
        if val:
            ganancia -= Decimal(str(val))
    return ganancia


def _enrich_tx(tx: Transaccion, vehiculo: Optional[Vehiculo] = None, cliente: Optional[Cliente] = None) -> dict:
    data = {c.name: getattr(tx, c.name) for c in tx.__table__.columns}
    precio_compra = Decimal(str(vehiculo.precio_compra)) if vehiculo and vehiculo.precio_compra else None
    ganancia = _calcular_ganancia(tx, precio_compra)
    data["ganancia_neta"] = ganancia
    data["margen_pct"] = (
        float(ganancia / precio_compra * 100) if (ganancia is not None and precio_compra and precio_compra > 0) else None
    )
    data["vehiculo_nombre"] = (
        f"{vehiculo.marca} {vehiculo.modelo} {vehiculo.anio}" if vehiculo else None
    )
    data["cliente_nombre"] = cliente.nombre if cliente else None
    return data


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=DashboardKPIs, summary="KPIs del dashboard")
async def dashboard(db: AsyncSession = Depends(get_db)):
    """
    Returns key performance indicators for the main dashboard:
    - Sales this month and year (count + COP amounts)
    - Average margin %, avg days to sell
    - Current inventory count and value
    """
    today = date.today()
    current_month = today.month
    current_year = today.year

    # All transactions
    all_tx_result = await db.execute(select(Transaccion))
    all_tx: list[Transaccion] = all_tx_result.scalars().all()

    # Pre-fetch vehicles and clients as dicts for O(1) lookup
    all_v_result = await db.execute(select(Vehiculo))
    vehiculos_map: dict[int, Vehiculo] = {v.id: v for v in all_v_result.scalars().all()}

    all_c_result = await db.execute(select(Cliente))
    clientes_map: dict[int, Cliente] = {c.id: c for c in all_c_result.scalars().all()}

    # Aggregate
    ventas_mes = 0
    ingresos_mes = Decimal(0)
    ganancia_mes = Decimal(0)
    margenes_mes: list[float] = []

    ventas_anio = 0
    ingresos_anio = Decimal(0)
    ganancia_anio = Decimal(0)

    total_tx = len(all_tx)
    tickets: list[Decimal] = []
    dias_venta: list[int] = []

    for tx in all_tx:
        vehiculo = vehiculos_map.get(tx.vehiculo_id)
        cliente = clientes_map.get(tx.cliente_id) if tx.cliente_id else None
        precio_compra = Decimal(str(vehiculo.precio_compra)) if vehiculo and vehiculo.precio_compra else None
        ganancia = _calcular_ganancia(tx, precio_compra)

        tx_date: date = tx.fecha if isinstance(tx.fecha, date) else tx.fecha.date()
        precio = Decimal(str(tx.precio_acordado))
        tickets.append(precio)

        if tx.tipo == "venta":
            if tx_date.year == current_year and tx_date.month == current_month:
                ventas_mes += 1
                ingresos_mes += precio
                if ganancia is not None:
                    ganancia_mes += ganancia
                    if precio_compra and precio_compra > 0:
                        margenes_mes.append(float(ganancia / precio_compra * 100))

            if tx_date.year == current_year:
                ventas_anio += 1
                ingresos_anio += precio
                if ganancia is not None:
                    ganancia_anio += ganancia

            # Days to sell
            if vehiculo and vehiculo.fecha_compra:
                dias = (tx_date - vehiculo.fecha_compra).days
                if dias >= 0:
                    dias_venta.append(dias)

    # Inventory stats
    disponibles = [v for v in vehiculos_map.values() if v.estado == "disponible"]
    valor_inv = sum(Decimal(str(v.precio_venta)) for v in disponibles if v.precio_venta)

    dias_inv: list[int] = []
    for v in disponibles:
        if v.fecha_compra:
            dias_inv.append((today - v.fecha_compra).days)

    return DashboardKPIs(
        ventas_mes_actual=ventas_mes,
        ingresos_mes_actual=ingresos_mes,
        ganancia_mes_actual=ganancia_mes,
        margen_promedio_mes=sum(margenes_mes) / len(margenes_mes) if margenes_mes else None,
        ventas_anio_actual=ventas_anio,
        ingresos_anio_actual=ingresos_anio,
        ganancia_anio_actual=ganancia_anio,
        vehiculos_disponibles=len(disponibles),
        valor_inventario_cop=valor_inv,
        dias_promedio_inventario=sum(dias_inv) / len(dias_inv) if dias_inv else None,
        tiempo_promedio_venta_dias=sum(dias_venta) / len(dias_venta) if dias_venta else None,
        total_transacciones=total_tx,
        ticket_promedio_cop=sum(tickets) / len(tickets) if tickets else None,
    )


@router.get("/reporte", response_model=ReporteResponse, summary="Reporte mensual/anual")
async def reporte(
    anio: int = Query(default=None, description="Año (default: año actual)"),
    mes: Optional[int] = Query(None, ge=1, le=12, description="Mes específico (opcional)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Monthly / yearly report.
    Returns per-month breakdown of sales count, revenue, costs, and net profit.
    """
    today = date.today()
    anio = anio or today.year

    conditions = [extract("year", Transaccion.fecha) == anio]
    if mes:
        conditions.append(extract("month", Transaccion.fecha) == mes)

    result = await db.execute(select(Transaccion).where(and_(*conditions)).order_by(Transaccion.fecha))
    txs: list[Transaccion] = result.scalars().all()

    all_v_result = await db.execute(select(Vehiculo))
    vehiculos_map: dict[int, Vehiculo] = {v.id: v for v in all_v_result.scalars().all()}

    # Group by month
    from collections import defaultdict
    meses_data: dict[int, dict] = defaultdict(lambda: {
        "ventas": 0, "compras": 0,
        "ingresos": Decimal(0), "gastos": Decimal(0),
        "ganancias": Decimal(0), "margenes": [],
        "tickets": [],
    })

    for tx in txs:
        tx_date: date = tx.fecha if isinstance(tx.fecha, date) else tx.fecha.date()
        m = tx_date.month
        vehiculo = vehiculos_map.get(tx.vehiculo_id)
        precio = Decimal(str(tx.precio_acordado))
        precio_compra = Decimal(str(vehiculo.precio_compra)) if vehiculo and vehiculo.precio_compra else None
        ganancia = _calcular_ganancia(tx, precio_compra)

        if tx.tipo == "venta":
            meses_data[m]["ventas"] += 1
            meses_data[m]["ingresos"] += precio
            meses_data[m]["tickets"].append(precio)
            if ganancia is not None:
                meses_data[m]["ganancias"] += ganancia
                if precio_compra and precio_compra > 0:
                    meses_data[m]["margenes"].append(float(ganancia / precio_compra * 100))
        elif tx.tipo == "compra":
            meses_data[m]["compras"] += 1
            meses_data[m]["gastos"] += precio

    # Build response
    meses_list: list[MesReporte] = []
    for m in sorted(meses_data.keys()):
        d = meses_data[m]
        margenes = d["margenes"]
        tickets = d["tickets"]
        meses_list.append(MesReporte(
            anio=anio,
            mes=m,
            ventas=d["ventas"],
            compras=d["compras"],
            ingresos_cop=d["ingresos"],
            gastos_cop=d["gastos"],
            ganancia_neta_cop=d["ganancias"],
            margen_pct=sum(margenes) / len(margenes) if margenes else None,
            ticket_promedio_cop=sum(tickets) / len(tickets) if tickets else None,
        ))

    total_ventas = sum(m.ventas for m in meses_list)
    total_ingresos = sum(m.ingresos_cop for m in meses_list)
    total_ganancia = sum(m.ganancia_neta_cop for m in meses_list)

    return ReporteResponse(
        periodo=f"{anio}" if not mes else f"{anio}-{mes:02d}",
        meses=meses_list,
        totales={
            "ventas": total_ventas,
            "ingresos_cop": total_ingresos,
            "ganancia_neta_cop": total_ganancia,
            "margen_promedio_pct": (
                float(total_ganancia / total_ingresos * 100)
                if total_ingresos > 0
                else None
            ),
        },
    )


@router.get("", response_model=list[TransaccionOut], summary="Listar transacciones")
async def listar_transacciones(
    tipo: Optional[str] = Query(None, description="compra | venta | consignacion"),
    vehiculo_id: Optional[int] = Query(None),
    cliente_id: Optional[int] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    conditions = []
    if tipo:
        conditions.append(Transaccion.tipo == tipo)
    if vehiculo_id:
        conditions.append(Transaccion.vehiculo_id == vehiculo_id)
    if cliente_id:
        conditions.append(Transaccion.cliente_id == cliente_id)
    if fecha_desde:
        conditions.append(Transaccion.fecha >= fecha_desde)
    if fecha_hasta:
        conditions.append(Transaccion.fecha <= fecha_hasta)

    stmt = select(Transaccion)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.offset(skip).limit(limit).order_by(Transaccion.fecha.desc())

    result = await db.execute(stmt)
    txs: list[Transaccion] = result.scalars().all()

    # Prefetch vehicles and clients
    if txs:
        v_ids = list({tx.vehiculo_id for tx in txs})
        c_ids = list({tx.cliente_id for tx in txs if tx.cliente_id})

        v_result = await db.execute(select(Vehiculo).where(Vehiculo.id.in_(v_ids)))
        vehiculos_map: dict[int, Vehiculo] = {v.id: v for v in v_result.scalars().all()}

        c_result = await db.execute(select(Cliente).where(Cliente.id.in_(c_ids)))
        clientes_map: dict[int, Cliente] = {c.id: c for c in c_result.scalars().all()}
    else:
        vehiculos_map = {}
        clientes_map = {}

    return [
        _enrich_tx(tx, vehiculos_map.get(tx.vehiculo_id), clientes_map.get(tx.cliente_id) if tx.cliente_id else None)
        for tx in txs
    ]


@router.get("/{transaccion_id}", response_model=TransaccionOut, summary="Obtener transacción por ID")
async def obtener_transaccion(transaccion_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaccion).where(Transaccion.id == transaccion_id))
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transacción no encontrada")

    v_result = await db.execute(select(Vehiculo).where(Vehiculo.id == tx.vehiculo_id))
    vehiculo = v_result.scalar_one_or_none()

    c_result = await db.execute(select(Cliente).where(Cliente.id == tx.cliente_id)) if tx.cliente_id else None
    cliente = (await c_result).scalar_one_or_none() if c_result else None

    return _enrich_tx(tx, vehiculo, cliente)


@router.post("", response_model=TransaccionOut, status_code=status.HTTP_201_CREATED, summary="Crear transacción")
async def crear_transaccion(payload: TransaccionCreate, db: AsyncSession = Depends(get_db)):
    # Validate vehiculo exists
    v_result = await db.execute(select(Vehiculo).where(Vehiculo.id == payload.vehiculo_id))
    vehiculo = v_result.scalar_one_or_none()
    if not vehiculo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado")

    # Validate cliente if provided
    cliente = None
    if payload.cliente_id:
        c_result = await db.execute(select(Cliente).where(Cliente.id == payload.cliente_id))
        cliente = c_result.scalar_one_or_none()
        if not cliente:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")

    tx = Transaccion(**payload.model_dump())
    db.add(tx)

    # Auto-update vehiculo estado based on tx type
    if payload.tipo == "venta":
        vehiculo.estado = "vendido"
        vehiculo.fecha_venta = payload.fecha
        vehiculo.precio_venta = payload.precio_acordado
    elif payload.tipo == "compra":
        vehiculo.estado = "disponible"
        vehiculo.fecha_compra = payload.fecha
        vehiculo.precio_compra = payload.precio_acordado

    await db.flush()
    await db.refresh(tx)
    return _enrich_tx(tx, vehiculo, cliente)


@router.put("/{transaccion_id}", response_model=TransaccionOut, summary="Actualizar transacción")
async def actualizar_transaccion(
    transaccion_id: int,
    payload: TransaccionUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Transaccion).where(Transaccion.id == transaccion_id))
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transacción no encontrada")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(tx, field, value)

    await db.flush()
    await db.refresh(tx)

    v_result = await db.execute(select(Vehiculo).where(Vehiculo.id == tx.vehiculo_id))
    vehiculo = v_result.scalar_one_or_none()
    c_result = await db.execute(select(Cliente).where(Cliente.id == tx.cliente_id)) if tx.cliente_id else None
    cliente = (await c_result).scalar_one_or_none() if c_result else None

    return _enrich_tx(tx, vehiculo, cliente)


@router.delete("/{transaccion_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar transacción")
async def eliminar_transaccion(transaccion_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaccion).where(Transaccion.id == transaccion_id))
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transacción no encontrada")
    await db.delete(tx)
