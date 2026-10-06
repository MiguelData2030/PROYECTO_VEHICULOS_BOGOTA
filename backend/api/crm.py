"""
Router: /crm (admin only) — sales pipeline follow-up.
A Seguimiento is one deal with a client; Interacciones are its touchpoints.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models import Cliente, Interaccion, Seguimiento, Vehiculo
from backend.models.crm import CANALES, ETAPAS, TIPOS_INTERACCION
from backend.models.database import get_db

router = APIRouter()

PROBABILIDAD = {"nuevo": 10, "contactado": 25, "cita": 45, "negociacion": 70, "ganado": 100, "perdido": 0}
ETAPA_LABEL = {"nuevo": "Nuevo", "contactado": "Contactado", "cita": "Cita / test drive",
               "negociacion": "Negociación", "ganado": "Ganado", "perdido": "Perdido"}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class NuevoCliente(BaseModel):
    nombre: str = Field(..., min_length=2)
    telefono: Optional[str] = None
    email: Optional[str] = None


class SeguimientoCreate(BaseModel):
    cliente_id: Optional[int] = None
    cliente_nuevo: Optional[NuevoCliente] = None
    vehiculo_id: Optional[int] = None
    tipo: str = "compra"
    canal: str = "whatsapp"
    valor_estimado: Optional[float] = None
    proxima_accion: Optional[str] = None
    fecha_proxima: Optional[date] = None
    responsable: Optional[str] = None
    notas: Optional[str] = None

    @field_validator("canal")
    @classmethod
    def canal_ok(cls, v: str) -> str:
        if v not in CANALES:
            raise ValueError(f"canal debe ser uno de {CANALES}")
        return v


class SeguimientoUpdate(BaseModel):
    etapa: Optional[str] = None
    vehiculo_id: Optional[int] = None
    valor_estimado: Optional[float] = None
    proxima_accion: Optional[str] = None
    fecha_proxima: Optional[date] = None
    responsable: Optional[str] = None
    motivo_perdida: Optional[str] = None
    notas: Optional[str] = None

    @field_validator("etapa")
    @classmethod
    def etapa_ok(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ETAPAS:
            raise ValueError(f"etapa debe ser una de {ETAPAS}")
        return v


class InteraccionCreate(BaseModel):
    tipo: str
    resumen: str = Field(..., min_length=2)

    @field_validator("tipo")
    @classmethod
    def tipo_ok(cls, v: str) -> str:
        if v not in TIPOS_INTERACCION:
            raise ValueError(f"tipo debe ser uno de {TIPOS_INTERACCION}")
        return v


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _out(s: Seguimiento, cli: Optional[Cliente], v: Optional[Vehiculo], con_historial: bool = False) -> dict:
    hoy = date.today()
    inter = s.interacciones or []
    data = {
        "id": s.id,
        "tipo": s.tipo,
        "etapa": s.etapa,
        "canal": s.canal,
        "valor_estimado": s.valor_estimado,
        "probabilidad": s.probabilidad,
        "proxima_accion": s.proxima_accion,
        "fecha_proxima": s.fecha_proxima,
        "vencida": bool(s.fecha_proxima and s.fecha_proxima < hoy and s.etapa not in ("ganado", "perdido")),
        "responsable": s.responsable,
        "motivo_perdida": s.motivo_perdida,
        "notas": s.notas,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
        "n_interacciones": len(inter),
        "ultima_interaccion": inter[-1].fecha if inter else None,
        "cliente": {
            "id": cli.id, "nombre": cli.nombre, "telefono": cli.telefono, "email": cli.email,
            "presupuesto_max": cli.presupuesto_max,
        } if cli else None,
        "vehiculo": {
            "id": v.id, "nombre": f"{v.marca} {v.modelo} {v.año}", "precio": v.precio_venta,
            "foto": (v.fotos or [None])[0], "estado": v.estado,
        } if v else None,
    }
    if con_historial:
        data["interacciones"] = [
            {"id": i.id, "tipo": i.tipo, "resumen": i.resumen, "fecha": i.fecha} for i in inter
        ]
    return data


async def _cargar(db: AsyncSession, seg_id: int) -> Seguimiento:
    s = (await db.execute(
        select(Seguimiento).options(selectinload(Seguimiento.interacciones)).where(Seguimiento.id == seg_id)
    )).scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seguimiento no encontrado")
    return s


async def crear_seguimiento_web(db: AsyncSession, cliente: Cliente, origen: str) -> None:
    """Called by the public forms: every web lead lands in the CRM as 'nuevo'."""
    tipo = "venta" if origen == "web_vender" or cliente.tipo == "vendedor" else "compra"
    s = Seguimiento(
        cliente_id=cliente.id, tipo=tipo, etapa="nuevo", canal="web", probabilidad=PROBABILIDAD["nuevo"],
        proxima_accion="Contactar lead de la web", fecha_proxima=date.today(), responsable=None,
        notas={"web_vender": "Formulario Vender", "web_contacto": "Formulario Contacto",
               "web_cotiza": "Cotizador ¿Cuánto vale tu carro?"}.get(origen, "Web"),
    )
    s.interacciones = [Interaccion(tipo="nota", resumen=f"Lead recibido desde la web ({s.notas}).")]
    db.add(s)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/resumen", summary="Indicadores del embudo comercial")
async def resumen(dias: int = Query(365, ge=7, le=730), db: AsyncSession = Depends(get_db)):
    segs = (await db.execute(select(Seguimiento))).scalars().all()
    hoy = date.today()
    desde = datetime.now(timezone.utc).timestamp() - dias * 86400

    def creado_ts(s: Seguimiento) -> float:
        c = s.created_at
        if c.tzinfo is None:
            c = c.replace(tzinfo=timezone.utc)
        return c.timestamp()

    recientes = [s for s in segs if creado_ts(s) >= desde]
    abiertos = [s for s in segs if s.etapa not in ("ganado", "perdido")]
    por_etapa = {e: {"cantidad": 0, "valor": 0.0} for e in ETAPAS}
    for s in abiertos + [s for s in recientes if s.etapa in ("ganado", "perdido")]:
        por_etapa[s.etapa]["cantidad"] += 1
        por_etapa[s.etapa]["valor"] += s.valor_estimado or 0

    canales: dict[str, dict] = defaultdict(lambda: {"leads": 0, "ganados": 0, "perdidos": 0, "valor_ganado": 0.0})
    for s in recientes:
        c = canales[s.canal]
        c["leads"] += 1
        if s.etapa == "ganado":
            c["ganados"] += 1
            c["valor_ganado"] += s.valor_estimado or 0
        elif s.etapa == "perdido":
            c["perdidos"] += 1
    for c in canales.values():
        cerrados = c["ganados"] + c["perdidos"]
        c["conversion_pct"] = round(c["ganados"] / cerrados * 100, 1) if cerrados else None

    ganados = [s for s in recientes if s.etapa == "ganado"]
    perdidos = [s for s in recientes if s.etapa == "perdido"]
    return {
        "por_etapa": por_etapa,
        "abiertos": len(abiertos),
        "valor_pipeline": sum(s.valor_estimado or 0 for s in abiertos),
        "valor_ponderado": sum((s.valor_estimado or 0) * (s.probabilidad or 0) / 100 for s in abiertos),
        "conversion_pct": round(len(ganados) / (len(ganados) + len(perdidos)) * 100, 1) if (ganados or perdidos) else None,
        "acciones_vencidas": sum(1 for s in abiertos if s.fecha_proxima and s.fecha_proxima < hoy),
        "acciones_hoy": sum(1 for s in abiertos if s.fecha_proxima == hoy),
        "por_canal": dict(sorted(canales.items(), key=lambda kv: -kv[1]["leads"])),
        "motivos_perdida": dict(Counter(s.motivo_perdida for s in perdidos if s.motivo_perdida).most_common()),
        "etapas": [{"key": e, "label": ETAPA_LABEL[e]} for e in ETAPAS],
    }


@router.get("", summary="Embudo comercial (seguimientos)")
async def listar(
    etapa: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None),
    responsable: Optional[str] = Query(None),
    incluir_cerrados_dias: int = Query(60, ge=0, le=730, description="Ganados/perdidos de los últimos N días"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Seguimiento).options(selectinload(Seguimiento.interacciones))
    if etapa:
        stmt = stmt.where(Seguimiento.etapa == etapa)
    if tipo:
        stmt = stmt.where(Seguimiento.tipo == tipo)
    if responsable:
        stmt = stmt.where(Seguimiento.responsable == responsable)
    segs = (await db.execute(stmt.order_by(Seguimiento.updated_at.desc()))).scalars().all()

    limite = datetime.now(timezone.utc).timestamp() - incluir_cerrados_dias * 86400

    def visible(s: Seguimiento) -> bool:
        if s.etapa not in ("ganado", "perdido") or etapa:
            return True
        u = s.updated_at if s.updated_at.tzinfo else s.updated_at.replace(tzinfo=timezone.utc)
        return u.timestamp() >= limite

    segs = [s for s in segs if visible(s)]
    clientes = {c.id: c for c in (await db.execute(
        select(Cliente).where(Cliente.id.in_({s.cliente_id for s in segs}))
    )).scalars().all()} if segs else {}
    v_ids = {s.vehiculo_id for s in segs if s.vehiculo_id}
    vehiculos = {v.id: v for v in (await db.execute(
        select(Vehiculo).where(Vehiculo.id.in_(v_ids))
    )).scalars().all()} if v_ids else {}
    return [_out(s, clientes.get(s.cliente_id), vehiculos.get(s.vehiculo_id)) for s in segs]


@router.get("/{seg_id}", summary="Detalle con historial de interacciones")
async def detalle(seg_id: int, db: AsyncSession = Depends(get_db)):
    s = await _cargar(db, seg_id)
    cli = await db.get(Cliente, s.cliente_id)
    v = await db.get(Vehiculo, s.vehiculo_id) if s.vehiculo_id else None
    return _out(s, cli, v, con_historial=True)


@router.post("", status_code=status.HTTP_201_CREATED, summary="Crear seguimiento")
async def crear(payload: SeguimientoCreate, db: AsyncSession = Depends(get_db)):
    if payload.cliente_id:
        cli = await db.get(Cliente, payload.cliente_id)
        if not cli:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
    elif payload.cliente_nuevo:
        cli = Cliente(
            nombre=payload.cliente_nuevo.nombre, telefono=payload.cliente_nuevo.telefono or None,
            email=payload.cliente_nuevo.email or None, tipo="vendedor" if payload.tipo == "venta" else "comprador",
        )
        db.add(cli)
        await db.flush()
    else:
        raise HTTPException(status_code=422, detail="Indica cliente_id o cliente_nuevo")

    v = await db.get(Vehiculo, payload.vehiculo_id) if payload.vehiculo_id else None
    s = Seguimiento(
        cliente_id=cli.id, vehiculo_id=v.id if v else None, tipo=payload.tipo, etapa="nuevo", canal=payload.canal,
        valor_estimado=payload.valor_estimado or (v.precio_venta if v else None),
        probabilidad=PROBABILIDAD["nuevo"], proxima_accion=payload.proxima_accion or "Primer contacto",
        fecha_proxima=payload.fecha_proxima or date.today(), responsable=payload.responsable, notas=payload.notas,
    )
    s.interacciones = [Interaccion(tipo="nota", resumen=f"Lead creado (canal: {payload.canal}).")]
    db.add(s)
    await db.flush()
    s = await _cargar(db, s.id)
    return _out(s, cli, v, con_historial=True)


@router.put("/{seg_id}", summary="Actualizar etapa / próxima acción")
async def actualizar(seg_id: int, payload: SeguimientoUpdate, db: AsyncSession = Depends(get_db)):
    s = await _cargar(db, seg_id)
    cambios = payload.model_dump(exclude_unset=True)
    etapa_anterior = s.etapa
    for k, v in cambios.items():
        setattr(s, k, v)
    if "etapa" in cambios and cambios["etapa"] != etapa_anterior:
        s.probabilidad = PROBABILIDAD[s.etapa]
        texto = f"Etapa: {ETAPA_LABEL[etapa_anterior]} → {ETAPA_LABEL[s.etapa]}"
        if s.etapa == "perdido" and s.motivo_perdida:
            texto += f" ({s.motivo_perdida})"
        s.interacciones.append(Interaccion(tipo="nota", resumen=texto + "."))
        if s.etapa in ("ganado", "perdido"):
            s.proxima_accion, s.fecha_proxima = None, None
    s.updated_at = datetime.now(timezone.utc)
    await db.flush()
    s = await _cargar(db, seg_id)
    cli = await db.get(Cliente, s.cliente_id)
    v = await db.get(Vehiculo, s.vehiculo_id) if s.vehiculo_id else None
    return _out(s, cli, v, con_historial=True)


@router.post("/{seg_id}/interacciones", status_code=status.HTTP_201_CREATED, summary="Registrar interacción")
async def agregar_interaccion(seg_id: int, payload: InteraccionCreate, db: AsyncSession = Depends(get_db)):
    s = await _cargar(db, seg_id)
    s.interacciones.append(Interaccion(tipo=payload.tipo, resumen=payload.resumen))
    s.updated_at = datetime.now(timezone.utc)
    await db.flush()
    s = await _cargar(db, seg_id)
    cli = await db.get(Cliente, s.cliente_id)
    v = await db.get(Vehiculo, s.vehiculo_id) if s.vehiculo_id else None
    return _out(s, cli, v, con_historial=True)


@router.delete("/{seg_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar seguimiento")
async def eliminar(seg_id: int, db: AsyncSession = Depends(get_db)):
    s = await _cargar(db, seg_id)
    await db.delete(s)
