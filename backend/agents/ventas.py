"""
Agente de Ventas — works the CRM pipeline like a sales manager:
prioritises who to contact today, matches each buyer's budget against the
inventory (alternatives) and drafts the next WhatsApp message.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.models import Cliente, Seguimiento, Vehiculo
from backend.models.database import AsyncSessionLocal
from .base_agent import ask_claude

SYSTEM_PROMPT = """Eres el Agente de Ventas de AutoNegocio, compraventa de usados en Bogotá.
Eres un jefe comercial experto en seguimiento de leads de redes sociales y WhatsApp:
sabes que la velocidad de respuesta cierra negocios y que nunca se deja un lead sin próxima
acción. Responde en español, en viñetas, máximo 180 palabras, con nombres y acciones concretas."""

PESO_ETAPA = {"nuevo": 30, "contactado": 20, "cita": 35, "negociacion": 45}
SIGUIENTE = {
    "nuevo": "Responder en menos de 1 hora con fotos, precio y simulación de crédito",
    "contactado": "Agendar visita o test drive esta semana",
    "cita": "Confirmar la cita y preparar el carro (lavado, papeles a la vista)",
    "negociacion": "Cerrar: contraoferta final y separar con abono",
}


def _cop(v) -> str:
    return f"${v:,.0f}".replace(",", ".") if v else "N/D"


def _aware(d: Optional[datetime]) -> Optional[datetime]:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


class AgenteVentas:
    async def analizar(self, limite: int = 15) -> dict:
        hoy = date.today()
        ahora = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as session:
            segs = (await session.execute(
                select(Seguimiento).options(selectinload(Seguimiento.interacciones))
                .where(Seguimiento.etapa.in_(list(PESO_ETAPA)))
            )).scalars().all()
            clientes = {c.id: c for c in (await session.execute(
                select(Cliente).where(Cliente.id.in_({s.cliente_id for s in segs}))
            )).scalars().all()} if segs else {}
            todos = (await session.execute(select(Vehiculo).where(Vehiculo.estado != "vendido"))).scalars().all()
        por_id = {v.id: v for v in todos}
        stock = [v for v in todos if v.estado in ("disponible", "reservado")]

        prioridades = []
        for s in segs:
            cli = clientes.get(s.cliente_id)
            ultima = _aware(s.interacciones[-1].fecha) if s.interacciones else _aware(s.created_at)
            dias_sin = max(0, (ahora - ultima).days) if ultima else 0
            vencida = bool(s.fecha_proxima and s.fecha_proxima < hoy)
            puntaje = PESO_ETAPA[s.etapa] + min(25, dias_sin * 5) + (20 if vencida else 0)
            puntaje += min(15, (s.valor_estimado or 0) / 10_000_000)
            if s.canal in ("instagram", "tiktok", "facebook", "whatsapp") and s.etapa == "nuevo":
                puntaje += 10  # social leads go cold within hours

            razones = []
            if vencida:
                razones.append(f"acción vencida desde {s.fecha_proxima.isoformat()}")
            if dias_sin >= 2:
                razones.append(f"{dias_sin} días sin contacto")
            if s.etapa == "negociacion":
                razones.append("está a un paso de cerrar")
            if s.etapa == "nuevo":
                razones.append(f"lead nuevo de {s.canal}")

            v = por_id.get(s.vehiculo_id) if s.vehiculo_id else None
            nombre = (cli.nombre.split()[0] if cli else "cliente")
            if s.tipo == "venta":
                accion, mensaje = {
                    "nuevo": ("Pedir fotos y datos del carro",
                              f"Hola {nombre} 👋 Gracias por pensar en AutoNegocio para vender tu carro. ¿Me compartes 4 fotos "
                              "(frente, lateral, interior y tablero con el kilometraje) para enviarte una oferta hoy mismo?"),
                    "contactado": ("Agendar peritaje sin costo",
                                   f"Hola {nombre}, con las fotos ya podemos avanzar. ¿Te queda bien traer el carro mañana "
                                   "para el peritaje? Es sin costo y en 40 minutos te damos la oferta."),
                    "cita": ("Enviar oferta (usa el Agente Valuador)",
                             f"Hola {nombre}, gracias por traer el carro. Te enviamos la oferta formal hoy; "
                             "pagamos de contado y hacemos el traspaso por ti."),
                    "negociacion": ("Cerrar compra con contraoferta final",
                                    f"Hola {nombre}, revisamos de nuevo y podemos mejorar un poco la oferta si cerramos "
                                    "esta semana. ¿Te llamo para concretar?"),
                }[s.etapa]
                alternativas = []
            else:
                accion = SIGUIENTE[s.etapa]
                presupuesto = (cli.presupuesto_max if cli and cli.presupuesto_max else None) or s.valor_estimado
                alternativas = self._alternativas(stock, v, presupuesto)
                carro = f"{v.marca} {v.modelo} {v.año}" if v else "carro que te interesa"
                mensaje = {
                    "nuevo": f"Hola {nombre} 👋 Soy de AutoNegocio. Te comparto fotos y la ficha del {carro}"
                             + (f" ({_cop(v.precio_venta)})" if v else "")
                             + ". ¿Lo quieres de contado o te simulo la cuota mensual?",
                    "contactado": f"Hola {nombre}, ¿cómo vas? El {carro} sigue disponible. "
                                  "¿Te queda bien venir a verlo y hacer test drive el sábado en la mañana?",
                    "cita": f"Hola {nombre}, te confirmo la cita para ver el {carro}. "
                            "Lo tenemos listo con los papeles a la vista. ¿Sigue en pie la hora?",
                    "negociacion": f"Hola {nombre}, hablé con gerencia: si separamos el {carro} esta semana "
                                   "te incluimos el traspaso. ¿Lo dejamos apartado con el abono?",
                }[s.etapa]
                if alternativas and s.etapa in ("nuevo", "contactado"):
                    mensaje += f" Si buscas otra opción en tu presupuesto, también tengo un {alternativas[0]['vehiculo']}."

            prioridades.append({
                "seguimiento_id": s.id,
                "cliente": cli.nombre if cli else "?",
                "telefono": cli.telefono if cli else None,
                "tipo": s.tipo,
                "etapa": s.etapa,
                "canal": s.canal,
                "vehiculo": f"{v.marca} {v.modelo} {v.año}" if v else None,
                "valor": s.valor_estimado,
                "responsable": s.responsable,
                "puntaje": round(puntaje),
                "razon": ", ".join(razones) or "seguimiento de rutina",
                "accion": accion,
                "mensaje": mensaje,
                "alternativas": alternativas,
            })

        prioridades.sort(key=lambda p: -p["puntaje"])
        abiertos = len(segs)
        vencidos = sum(1 for s in segs if s.fecha_proxima and s.fecha_proxima < hoy)
        sin_responsable = sum(1 for s in segs if not s.responsable)
        nuevos_redes = sum(1 for s in segs if s.etapa == "nuevo" and s.canal in ("instagram", "tiktok", "facebook", "whatsapp"))
        ponderado = sum((s.valor_estimado or 0) * {"nuevo": .1, "contactado": .25, "cita": .45, "negociacion": .7}[s.etapa] for s in segs)

        resultado = {
            "abiertos": abiertos,
            "vencidos": vencidos,
            "sin_responsable": sin_responsable,
            "nuevos_redes": nuevos_redes,
            "valor_ponderado": ponderado,
            "prioridades": prioridades[:limite],
        }
        texto = await self._ia(resultado)
        resultado["analisis"] = texto or self._base(resultado)
        resultado["analisis_ia"] = texto is not None
        return resultado

    @staticmethod
    def _alternativas(stock: list[Vehiculo], actual: Optional[Vehiculo], presupuesto: Optional[float]) -> list[dict]:
        if not presupuesto:
            return []
        tipo = actual.tipo_vehiculo if actual else None
        candidatos = [
            v for v in stock
            if v.estado == "disponible" and v.precio_venta and (not actual or v.id != actual.id)
            and 0.8 * presupuesto <= v.precio_venta <= 1.08 * presupuesto
        ]
        candidatos.sort(key=lambda v: (v.tipo_vehiculo != tipo, abs(v.precio_venta - presupuesto)))
        return [{"vehiculo_id": v.id, "vehiculo": f"{v.marca} {v.modelo} {v.año}", "precio": v.precio_venta,
                 "foto": (v.fotos or [None])[0]} for v in candidatos[:3]]

    @staticmethod
    def _base(r: dict) -> str:
        top = r["prioridades"][:3]
        lineas = [f"{r['abiertos']} negocios abiertos por {_cop(r['valor_ponderado'])} ponderados; "
                  f"{r['vencidos']} con la acción vencida."]
        if r["nuevos_redes"]:
            lineas.append(f"{r['nuevos_redes']} leads nuevos de redes esperan respuesta: contestar en menos de 1 hora "
                          "multiplica la probabilidad de cierre.")
        if r["sin_responsable"]:
            lineas.append(f"{r['sin_responsable']} lead(s) sin asesor asignado.")
        if top:
            lineas.append("Llamar primero a: " + "; ".join(f"{p['cliente']} ({p['razon']})" for p in top) + ".")
        return "\n".join(f"• {x}" for x in lineas)

    async def _ia(self, r: dict) -> Optional[str]:
        if not r["prioridades"]:
            return None
        lista = "\n".join(
            f"- {p['cliente']} | {p['etapa']} | {p['canal']} | {p['vehiculo'] or p['tipo']} | {_cop(p['valor'])} | {p['razon']}"
            for p in r["prioridades"][:10]
        )
        prompt = f"""Embudo comercial hoy: {r['abiertos']} negocios abiertos, {r['vencidos']} vencidos,
{r['nuevos_redes']} leads nuevos de redes sin responder, valor ponderado {_cop(r['valor_ponderado'])}.
Prioridades calculadas:
{lista}

Da: (1) plan de llamadas para hoy en orden, (2) un consejo para cada uno de los 3 primeros,
(3) qué hábito comercial corregir según estos datos."""
        return await ask_claude(prompt, system=SYSTEM_PROMPT)
