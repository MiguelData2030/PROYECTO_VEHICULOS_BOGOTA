"""
Router: /publico — public endpoints (no login).

POST /publico/cotizar: "¿Cuánto vale tu carro?" — instant market range and an
estimated purchase offer from AutoNegocio, computed by the Agente Valuador.
If the visitor accepts to be contacted (data-processing consent, Ley 1581),
they are stored as a seller lead and a deal is created in the CRM.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Cliente
from backend.models.database import get_db

router = APIRouter()

# Simple in-memory rate limit: 15 quotes per IP per hour
_hits: dict[str, deque] = defaultdict(deque)
LIMITE, VENTANA = 15, 3600


def _rate_limit(request: Request) -> None:
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "?").split(",")[0].strip()
    ahora = time.time()
    q = _hits[ip]
    while q and ahora - q[0] > VENTANA:
        q.popleft()
    if len(q) >= LIMITE:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Demasiadas cotizaciones. Intenta de nuevo en un rato o escríbenos por WhatsApp.")
    q.append(ahora)


class CotizacionIn(BaseModel):
    marca: str = Field(..., min_length=2, max_length=50)
    modelo: str = Field(..., min_length=1, max_length=60)
    año: int = Field(..., ge=1995, le=2030)
    kilometraje: int = Field(..., ge=0, le=600_000)
    transmision: str = "automatica"
    combustible: str = "gasolina"
    estado_mecanico: str = "bueno"
    # Optional contact (only stored with consent)
    nombre: Optional[str] = Field(None, max_length=120)
    telefono: Optional[str] = Field(None, max_length=30)
    email: Optional[EmailStr] = None
    acepta_contacto: bool = False


@router.post("/cotizar", summary="¿Cuánto vale tu carro? (público)")
async def cotizar(payload: CotizacionIn, request: Request, db: AsyncSession = Depends(get_db)):
    _rate_limit(request)
    from backend.agents.valuador import AgenteValuador

    r = await AgenteValuador().valuate(
        marca=payload.marca, modelo=payload.modelo, año=payload.año, kilometraje=payload.kilometraje,
        transmision=payload.transmision, combustible=payload.combustible,
        estado_mecanico=payload.estado_mecanico,
    )
    valor = r.get("valor_mercado")

    lead_guardado = False
    if payload.acepta_contacto and payload.nombre and (payload.telefono or payload.email):
        from backend.api.crm import crear_seguimiento_web

        carro = f"{payload.marca} {payload.modelo} {payload.año}"
        cliente = None
        if payload.telefono:
            cliente = (await db.execute(select(Cliente).where(Cliente.telefono == payload.telefono))).scalar_one_or_none()
        nota = (f"Cotizador web: {carro}, {payload.kilometraje:,} km. "
                f"Rango mostrado: {r['rango_mercado']}. Autorizó tratamiento de datos.").replace(",", ".")
        if cliente:
            cliente.notas = f"{cliente.notas or ''}\n{nota}".strip()
        else:
            cliente = Cliente(
                nombre=payload.nombre, telefono=payload.telefono, email=payload.email, tipo="vendedor", notas=nota,
                vehiculos_interes=[{"marca": payload.marca, "modelo": payload.modelo, "anio": payload.año,
                                    "kilometraje": payload.kilometraje}],
            )
            db.add(cliente)
            await db.flush()
        await crear_seguimiento_web(db, cliente, "web_cotiza")
        lead_guardado = True

    if not valor:
        return {
            "encontrado": False,
            "mensaje": "No tenemos suficientes datos de ese modelo para darte un rango automático. "
                       "Déjanos tus datos o escríbenos por WhatsApp y un asesor te cotiza hoy mismo.",
            "lead_guardado": lead_guardado,
        }

    # Only show factors based on data the visitor actually gave us
    # (color and number of owners are not asked in the public form).
    def propio(f: str) -> bool:
        return not (f.startswith("Color") or "dueño" in f)

    return {
        "encontrado": True,
        "rango_mercado": r["rango_mercado"],
        "valor_mercado": valor,
        # What a dealer would realistically pay (subject to inspection)
        "oferta_estimada": [r["precio_compra_ideal"], r["precio_compra_maximo"]],
        "liquidez": r["liquidez"],
        "dias_estimados_venta": r["dias_estimados_venta"],
        "factores_positivos": [f for f in r["factores_positivos"] if propio(f)][:4],
        "factores_negativos": [f for f in r["factores_negativos"] if propio(f)][:3],
        "comparables": len(r["comparables"]),
        "metodo": r["metodo"],
        "lead_guardado": lead_guardado,
    }
