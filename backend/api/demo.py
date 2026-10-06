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

from backend.demo.generator import DEMO_EMAIL_DOMAIN, DEMO_TAG, build_demo_full
from backend.models import (
    Cliente, Interaccion, Publicacion, RedMetrica, Seguimiento, Transaccion, Vehiculo,
)
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
    segs = (await db.execute(select(func.count(Seguimiento.id)).where(Seguimiento.demo.is_(True)))).scalar_one()
    pubs = (await db.execute(select(func.count(Publicacion.id)).where(Publicacion.demo.is_(True)))).scalar_one()
    return {"cargado": bool(v_ids), "vehiculos": len(v_ids), "clientes": len(c_ids), "transacciones": tx,
            "seguimientos": segs, "publicaciones": pubs}


@router.post("", status_code=status.HTTP_201_CREATED, summary="Cargar un año simulado de operación")
async def cargar_demo(db: AsyncSession = Depends(get_db)):
    v_ids, _ = await _demo_ids(db)
    if v_ids:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Los datos de demostración ya están cargados")

    data = build_demo_full()
    clientes, vehiculos = data["clientes"], data["vehiculos"]

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
    veh_rows: dict[str, Vehiculo] = {}
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
        veh_rows[v.ref] = row

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

    # CRM pipeline with its interaction history
    for sg in data["seguimientos"]:
        seg = Seguimiento(
            cliente_id=cli_rows[sg.cliente_ref].id,
            vehiculo_id=veh_rows[sg.vehiculo_ref].id if sg.vehiculo_ref else None,
            tipo=sg.tipo, etapa=sg.etapa, canal=sg.canal, valor_estimado=sg.valor_estimado,
            probabilidad=sg.probabilidad, proxima_accion=sg.proxima_accion, fecha_proxima=sg.fecha_proxima,
            responsable=sg.responsable, motivo_perdida=sg.motivo_perdida, notas=sg.notas, demo=True,
        )
        seg.created_at = sg.creado
        seg.updated_at = max((i[0] for i in sg.interacciones), default=sg.creado)
        seg.interacciones = [Interaccion(tipo=t, resumen=r, fecha=f, demo=True) for f, t, r in sg.interacciones]
        db.add(seg)

    # Social networks
    for m in data["metricas"]:
        db.add(RedMetrica(**m, demo=True))
    for p in data["publicaciones"]:
        ref = p.pop("vehiculo_ref", None)
        db.add(Publicacion(**p, vehiculo_id=veh_rows[ref].id if ref in veh_rows else None, demo=True))

    await db.flush()
    return {"vehiculos": len(vehiculos), "clientes": len(clientes), "transacciones": n_tx,
            "seguimientos": len(data["seguimientos"]), "publicaciones": len(data["publicaciones"])}


@router.delete("", summary="Borrar todos los datos de demostración")
async def borrar_demo(db: AsyncSession = Depends(get_db)):
    v_ids, c_ids = await _demo_ids(db)
    # CRM and social rows first, then transactions (FKs), vehicles and clients
    await db.execute(delete(Interaccion).where(Interaccion.demo.is_(True)))
    await db.execute(delete(Seguimiento).where(Seguimiento.demo.is_(True)))
    await db.execute(delete(Publicacion).where(Publicacion.demo.is_(True)))
    await db.execute(delete(RedMetrica).where(RedMetrica.demo.is_(True)))
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
