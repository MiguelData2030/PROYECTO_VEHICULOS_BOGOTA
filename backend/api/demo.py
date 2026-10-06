"""
Router: /demo — load or remove the simulated year of operation (admin only).

Demo rows are tagged (see backend.demo.generator) so removing them never
touches real inventory, clients or sales.
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.demo.generator import DEMO_EMAIL_DOMAIN, DEMO_TAG, build_demo
from backend.models import Cliente, Transaccion, Vehiculo
from backend.models.database import get_db

router = APIRouter()


def _dt(d: date, hour: int = 12) -> datetime:
    return datetime.combine(d, time(hour, 0), tzinfo=timezone.utc)


async def _demo_ids(db: AsyncSession) -> tuple[list[int], list[int]]:
    v_ids = (await db.execute(select(Vehiculo.id).where(Vehiculo.url_fuente == DEMO_TAG))).scalars().all()
    c_ids = (await db.execute(
        select(Cliente.id).where(Cliente.email.like(f"%@{DEMO_EMAIL_DOMAIN}"))
    )).scalars().all()
    return list(v_ids), list(c_ids)


@router.get("", summary="¿Hay datos de demostración cargados?")
async def estado_demo(db: AsyncSession = Depends(get_db)):
    v_ids, c_ids = await _demo_ids(db)
    tx = 0
    if v_ids:
        tx = (await db.execute(
            select(func.count(Transaccion.id)).where(Transaccion.vehiculo_id.in_(v_ids))
        )).scalar_one()
    return {"cargado": bool(v_ids), "vehiculos": len(v_ids), "clientes": len(c_ids), "transacciones": tx}


@router.post("", status_code=status.HTTP_201_CREATED, summary="Cargar un año simulado de operación")
async def cargar_demo(db: AsyncSession = Depends(get_db)):
    v_ids, _ = await _demo_ids(db)
    if v_ids:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Los datos de demostración ya están cargados")

    clientes, vehiculos = build_demo()

    cli_rows: dict[str, Cliente] = {}
    for c in clientes:
        row = Cliente(
            nombre=c.nombre, email=c.email, tipo=c.tipo, notas=c.notas,
            vehiculos_interes=c.vehiculos_interes, presupuesto_min=c.presupuesto_min,
            presupuesto_max=c.presupuesto_max,
        )
        if c.creado:
            row.created_at = _dt(c.creado, 10)
        cli_rows[c.ref] = row
        db.add(row)
    await db.flush()

    n_tx = 0
    for v in vehiculos:
        datos = dict(v.datos)
        venta = v.venta
        row = Vehiculo(
            **datos,
            fecha_compra=_dt(v.fecha_compra),
            fecha_publicacion=_dt(v.fecha_compra, 18),
            fecha_venta=_dt(venta["fecha"]) if venta else None,
        )
        row.created_at = _dt(v.fecha_compra)
        db.add(row)
        await db.flush()

        db.add(Transaccion(
            vehiculo_id=row.id, cliente_id=cli_rows[v.vendedor_ref].id, tipo="compra",
            precio=v.precio_compra, gastos_traspaso=v.gastos_compra,
            gastos_reacondicionamiento=v.reacondicionamiento, comision=0.0,
            fecha=_dt(v.fecha_compra), notas=f"[DEMO] Compra ({datos['fuente']}).",
        ))
        n_tx += 1
        if venta:
            ganancia = (venta["precio"] - v.precio_compra - v.gastos_compra
                        - v.reacondicionamiento - venta["comision"] - venta["gastos_traspaso"])
            db.add(Transaccion(
                vehiculo_id=row.id, cliente_id=cli_rows[venta["cliente_ref"]].id, tipo="venta",
                precio=venta["precio"], comision=venta["comision"],
                gastos_traspaso=venta["gastos_traspaso"], gastos_reacondicionamiento=0.0,
                ganancia_neta=ganancia, fecha=_dt(venta["fecha"]), notas=venta["notas"],
            ))
            n_tx += 1

    await db.flush()
    return {"vehiculos": len(vehiculos), "clientes": len(clientes), "transacciones": n_tx}


@router.delete("", summary="Borrar todos los datos de demostración")
async def borrar_demo(db: AsyncSession = Depends(get_db)):
    v_ids, c_ids = await _demo_ids(db)
    # Transactions first (FKs), then vehicles and clients
    conds = []
    if v_ids:
        conds.append(Transaccion.vehiculo_id.in_(v_ids))
    if c_ids:
        conds.append(Transaccion.cliente_id.in_(c_ids))
    for cond in conds:
        await db.execute(delete(Transaccion).where(cond))
    if v_ids:
        await db.execute(delete(Vehiculo).where(Vehiculo.id.in_(v_ids)))
    if c_ids:
        await db.execute(delete(Cliente).where(Cliente.id.in_(c_ids)))
    return {"vehiculos": len(v_ids), "clientes": len(c_ids)}
