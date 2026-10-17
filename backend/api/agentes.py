"""
Router: /agentes (admin only)
AI agents: Valuador (pricing), Cazador (buying opportunities), Marketing
(strategy + sales copy), Financiero, Ventas, and the operations agents
Logística (routes), Alistamiento (workshop), Crédito (pre-qualification) and
Atención 24/7 (first reply to messages). All work without an API key; with
ANTHROPIC_API_KEY they add a written analysis by Claude.
"""

from __future__ import annotations

import random
from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents import alistamiento, atencion, credito, logistica
from backend.agents import datos_simulados as sim
from backend.agents.base_agent import ia_disponible
from backend.config.settings import settings
from backend.models import Cliente, Interaccion, Seguimiento, Vehiculo
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
        "agentes": ["valuador", "cazador", "marketing", "financiero", "ventas",
                    "logistica", "alistamiento", "credito", "atencion"],
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


# Declared before /marketing/{vehiculo_id} so "estrategia" is not parsed as an id
@router.post("/marketing/estrategia", summary="Agente de Marketing: estrategia, presupuesto y calendario de contenido")
async def marketing_estrategia(
    dias: int = Query(90, ge=14, le=365, description="Periodo de datos a analizar"),
    presupuesto: Optional[float] = Query(None, ge=0, description="Pauta mensual (COP); vacío = la que se gasta hoy"),
):
    from backend.agents.marketing import AgenteMarketing

    return await AgenteMarketing().estrategia(dias=dias, presupuesto=presupuesto)


@router.post("/marketing/{vehiculo_id}", summary="Agente de Marketing: textos de venta de un vehículo")
async def marketing(vehiculo_id: int, db: AsyncSession = Depends(get_db)):
    from backend.agents.marketing import AgenteMarketing

    vehiculo = await db.get(Vehiculo, vehiculo_id)
    if not vehiculo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado")
    return await AgenteMarketing().redactar(vehiculo)


@router.post("/financiero", summary="Agente Financiero: flujo de caja, capital, rebajas y rentabilidad")
async def financiero():
    from backend.agents.financiero import AgenteFinanciero

    return await AgenteFinanciero().analizar()


@router.post("/ventas", summary="Agente de Ventas: prioridades del CRM y mensajes sugeridos")
async def ventas(limite: int = Query(15, ge=1, le=50)):
    from backend.agents.ventas import AgenteVentas

    return await AgenteVentas().analizar(limite=limite)


# ---------------------------------------------------------------------------
# Operations agents (Logística, Alistamiento, Crédito, Atención)
# ---------------------------------------------------------------------------

LIQUIDEZ_ALTA = {"Toyota", "Mazda", "Chevrolet", "Renault", "Kia"}


async def _inventario(db: AsyncSession) -> list[dict]:
    """Cars for sale in the agents' format; the sample inventory if there are none yet."""
    filas = (await db.execute(
        select(Vehiculo).where(Vehiculo.estado.in_(("disponible", "reservado")), Vehiculo.precio_venta.isnot(None))
    )).scalars().all()
    if not filas:
        return sim.inventario()
    return [{
        "id": v.id, "marca": v.marca, "modelo": v.modelo, "año": v.año, "kilometraje": v.kilometraje,
        "tipo": v.tipo_vehiculo, "precio": v.precio_venta,
        "liquidez": "alta" if v.marca in LIQUIDEZ_ALTA else "media",
    } for v in filas]


# --- Logística ---------------------------------------------------------------

class CitaIn(BaseModel):
    id: str = Field(..., max_length=20)
    tipo: Literal["peritaje", "entrega", "test_drive"]
    cliente: str = Field("Cliente", max_length=100)
    zona: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    desde: str = Field("08:00", pattern=r"^\d{2}:\d{2}$")
    hasta: str = Field("17:30", pattern=r"^\d{2}:\d{2}$")
    duracion_min: Optional[int] = Field(None, ge=10, le=240)


class LogisticaRequest(BaseModel):
    citas: list[CitaIn] = Field(..., min_length=1, max_length=60)
    conductores: int = Field(2, ge=1, le=6)


DURACION = {"peritaje": 45, "entrega": 60, "test_drive": 40}


@router.get("/logistica/agenda", summary="Agente de Logística: agenda de ejemplo del día")
async def logistica_agenda(semilla: int = Query(sim.SEMILLA), n: int = Query(18, ge=3, le=40)):
    return {"sede": sim.SEDE, "zonas": list(sim.ZONAS), "citas": sim.citas_del_dia(random.Random(semilla), n)}


@router.post("/logistica", summary="Agente de Logística: rutas del día con ventanas horarias")
async def logistica_rutas(payload: LogisticaRequest):
    citas = []
    for c in payload.citas:
        if c.zona not in sim.ZONAS and (c.lat is None or c.lon is None):
            raise HTTPException(status_code=422, detail=f"Zona desconocida: {c.zona}")
        if c.hasta <= c.desde:
            raise HTTPException(status_code=422, detail=f"La ventana de {c.id} termina antes de empezar")
        d = c.model_dump()
        if d["lat"] is None or d["lon"] is None:
            # a point near the zone centre, stable for the same cita
            rng = random.Random(c.id + c.zona)
            lat, lon = sim.ZONAS[c.zona]
            d["lat"] = round(lat + rng.uniform(-0.006, 0.006), 5)
            d["lon"] = round(lon + rng.uniform(-0.006, 0.006), 5)
        d["duracion_min"] = d["duracion_min"] or DURACION[c.tipo]
        citas.append(d)
    plan = logistica.analizar(sim.SEDE, citas, payload.conductores)
    plan["zonas"] = [{"nombre": z, "lat": lat, "lon": lon} for z, (lat, lon) in sim.ZONAS.items()]
    return plan


# --- Alistamiento ------------------------------------------------------------

class AlistamientoRequest(BaseModel):
    semilla: int = sim.SEMILLA
    carros: int = Field(14, ge=3, le=40)
    capacidad: dict[str, int] = Field(default_factory=dict, description="Cupos por área; vacío = los de siempre")


@router.post("/alistamiento", summary="Agente de Alistamiento: orden del taller y cuello de botella")
async def alistamiento_plan(payload: AlistamientoRequest, db: AsyncSession = Depends(get_db)):
    lote = sim.compras_por_alistar(random.Random(payload.semilla), await _inventario(db), payload.carros)
    capacidad = {k: max(1, min(6, v)) for k, v in payload.capacidad.items() if k in alistamiento.CAPACIDAD}
    return {**alistamiento.analizar(lote, capacidad), "lote": lote}


# --- Crédito -----------------------------------------------------------------

class CreditoRequest(BaseModel):
    cliente: str = Field("Cliente", max_length=100)
    empleo: Literal["empleado", "independiente", "pensionado"] = "empleado"
    ingreso_mensual: float = Field(..., gt=0)
    cuotas_actuales: float = Field(0, ge=0)
    puntaje_buro: int = Field(..., ge=150, le=950)
    vehiculo_id: Optional[int] = None
    precio: Optional[float] = Field(None, gt=0, description="Si no se elige un carro del inventario")
    cuota_inicial: float = Field(0, ge=0)


@router.post("/credito", summary="Agente de Crédito: precalificar a un comprador")
async def credito_evaluar(payload: CreditoRequest, db: AsyncSession = Depends(get_db)):
    inv = await _inventario(db)
    carro = next((v for v in inv if v["id"] == payload.vehiculo_id), None) if payload.vehiculo_id else None
    precio = carro["precio"] if carro else payload.precio
    if not precio:
        raise HTTPException(status_code=422, detail="Elige un carro del inventario o escribe el precio")
    if payload.cuota_inicial >= precio:
        raise HTTPException(status_code=422, detail="La cuota inicial cubre todo el precio: es una compra de contado")
    solicitud = {
        "id": "S01", "cliente": payload.cliente, "empleo": payload.empleo,
        "ingreso_mensual": payload.ingreso_mensual, "cuotas_actuales": payload.cuotas_actuales,
        "puntaje_buro": payload.puntaje_buro, "vehiculo_id": payload.vehiculo_id,
        "vehiculo": f"{carro['marca']} {carro['modelo']} {carro['año']}" if carro else "carro elegido",
        "precio": precio, "cuota_inicial": payload.cuota_inicial,
    }
    otros = [v for v in inv if not carro or v["id"] != carro["id"]]
    r = credito.evaluar(solicitud, otros)
    ea = credito.tasa_ea(payload.puntaje_buro)
    r["tabla"] = [
        {"plazo": m, "cuota": round(credito.cuota(precio - payload.cuota_inicial, ea, m), -3)}
        for m in credito.PLAZOS
    ] if ea else []
    return r


@router.post("/credito/simulacion", summary="Agente de Crédito: simular un lote de solicitudes")
async def credito_simulacion(semilla: int = Query(sim.SEMILLA), n: int = Query(25, ge=5, le=100),
                             db: AsyncSession = Depends(get_db)):
    inv = await _inventario(db)
    return credito.analizar(sim.solicitudes_credito(random.Random(semilla), inv, n), inv)


# --- Atención 24/7 -----------------------------------------------------------

class MensajeIn(BaseModel):
    mensaje: str = Field(..., min_length=2, max_length=1000)
    canal: Literal["whatsapp", "instagram", "facebook", "tiktok", "web"] = "whatsapp"
    cliente: str = Field("Cliente", max_length=100)
    telefono: Optional[str] = Field(None, max_length=30)
    guardar_lead: bool = False


@router.post("/atencion", summary="Agente de Atención 24/7: responder un mensaje")
async def atencion_responder(payload: MensajeIn, db: AsyncSession = Depends(get_db)):
    m = {"id": "M01", "canal": payload.canal, "cliente": payload.cliente, "hora": "",
         "texto": payload.mensaje, "intencion_real": None}
    r = await atencion.responder_con_ia(m, await _inventario(db))
    r.pop("acierto", None)
    r["lead_id"] = None
    if payload.guardar_lead and r["intencion"] != "otro":
        vende = r["intencion"] == "vender"
        cliente = Cliente(nombre=payload.cliente, telefono=payload.telefono,
                          tipo="vendedor" if vende else "comprador", presupuesto_max=r["presupuesto"],
                          notas=f"Mensaje por {payload.canal}: {payload.mensaje}")
        db.add(cliente)
        await db.flush()
        seg = Seguimiento(
            cliente_id=cliente.id, tipo="venta" if vende else "compra", etapa="nuevo",
            canal=payload.canal, valor_estimado=r["presupuesto"], probabilidad=10,
            proxima_accion="Atender la queja" if r["intencion"] == "queja" else "Llamar: lead del Agente de Atención",
            fecha_proxima=date.today(), notas=f"Lead {r['temperatura']} creado por el Agente de Atención",
        )
        seg.interacciones = [
            Interaccion(tipo="mensaje_red", resumen=f"Cliente: {payload.mensaje}"),
            Interaccion(tipo="mensaje_red", resumen=f"Agente: {r['respuesta']}"),
        ]
        db.add(seg)
        await db.commit()
        r["lead_id"] = seg.id
    return r


@router.post("/atencion/simulacion", summary="Agente de Atención 24/7: simular un día de mensajes")
async def atencion_simulacion(semilla: int = Query(sim.SEMILLA), n: int = Query(40, ge=5, le=100),
                              db: AsyncSession = Depends(get_db)):
    return atencion.analizar(sim.mensajes_entrantes(random.Random(semilla), n), await _inventario(db))
