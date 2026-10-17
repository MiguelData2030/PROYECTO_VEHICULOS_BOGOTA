"""
Agente de Atención 24/7 — primera respuesta a los mensajes de WhatsApp y
redes sociales, a cualquier hora.

Para cada mensaje:
  1. Detecta la intención: comprar, vender, financiación, disponibilidad de un
     carro, cita o queja.
  2. Extrae los datos útiles: marca, tipo de carro, presupuesto, ingreso,
     urgencia ("esta semana", "de contado").
  3. Responde con datos reales del inventario (carros que encajan, precios)
     y crea el lead en el CRM con su temperatura (caliente, tibio, frío).
  4. Pasa a un asesor humano las quejas y lo que no entiende con seguridad.

En la simulación la intención se detecta con palabras clave. En producción,
Claude clasifica y redacta la respuesta, y las palabras clave quedan como
respaldo (igual que en los 5 agentes actuales).
"""

from __future__ import annotations

import re
import unicodedata

PALABRAS = {
    "queja": ["no funciona", "mal servicio", "reclamo", "esperando", "necesito que me respondan", "garantia"],
    "financiacion": ["financian", "cuota", "credito", "datacredito", "reportado", "inicial", "gano"],
    "vender": ["vender mi", "compran carros", "cuanto me dan", "me pagan", "vendo", "vender"],
    "disponibilidad": ["disponible", "publicaron", "vi el", "sigue"],
    "cita": ["donde quedan", "test drive", "abren", "ir a ver", "direccion", "horario"],
    "comprar": ["busco", "buscando", "necesito un carro", "quiero comprar", "que tienen", "presupuesto"],
}
# Si dos intenciones empatan, gana la primera de esta lista
PRIORIDAD = ["queja", "financiacion", "vender", "disponibilidad", "cita", "comprar"]
MARCAS = ["mazda", "toyota", "kia", "chevrolet", "renault", "hyundai", "nissan", "ford", "volkswagen", "suzuki"]
TIPOS = {"camioneta": "SUV", "suv": "SUV", "sedan": "Sedan", "hatchback": "Hatchback"}
RESPUESTA_HUMANO_MIN = 47   # tiempo medio de primera respuesta de un asesor (supuesto)


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _cop(v: float) -> str:
    return f"${v:,.0f}".replace(",", ".")


def _km(v: int) -> str:
    return f"{v:,}".replace(",", ".")


def entender(texto: str) -> dict:
    t = _norm(texto)
    puntos = {i: sum(1 for p in PALABRAS[i] if p in t) for i in PRIORIDAD}
    mejor = max(PRIORIDAD, key=lambda i: (puntos[i], -PRIORIDAD.index(i)))
    segundo = sorted(puntos.values(), reverse=True)[1]
    confianza = "alta" if puntos[mejor] >= 2 or (puntos[mejor] == 1 and segundo == 0) else "baja"
    if puntos[mejor] == 0:
        mejor, confianza = "otro", "baja"
    millones = re.search(r"(\d{2,3})\s*(millones|palos|m\b)", t)
    ingreso = re.search(r"gano\s*(\d{1,2})\s*millones", t)
    return {
        "intencion": mejor,
        "confianza": confianza,
        "marca": next((m.capitalize() for m in MARCAS if m in t), None),
        "tipo": next((v for k, v in TIPOS.items() if k in t), None),
        "presupuesto": int(millones.group(1)) * 1_000_000 if millones and not ingreso else None,
        "ingreso": int(ingreso.group(1)) * 1_000_000 if ingreso else None,
        "urgente": any(p in t for p in ("esta semana", "hoy", "rapido", "de contado", "urgente")),
    }


def _carros(inv: list[dict], e: dict, n: int = 2) -> list[dict]:
    c = [v for v in inv
         if (not e["marca"] or v["marca"] == e["marca"])
         and (not e["tipo"] or v["tipo"] == e["tipo"])
         and (not e["presupuesto"] or v["precio"] <= e["presupuesto"])]
    return sorted(c, key=lambda v: -v["precio"])[:n]


def responder(m: dict, inv: list[dict]) -> dict:
    e = entender(m["texto"])
    nombre = m["cliente"].split()[0]
    humano, temp = False, "tibio"
    i = e["intencion"]
    if i == "queja" or e["confianza"] == "baja":
        humano, temp = True, "—"
        texto = (f"Hola {nombre}, lamento la situación. Ya le pasé tu caso a un asesor que te escribe en los "
                 "próximos minutos." if i == "queja" else
                 f"Hola {nombre}, gracias por escribir. Un asesor te responde en un momento.")
    elif i in ("comprar", "disponibilidad"):
        carros = _carros(inv, e)
        if carros:
            lista = "; ".join(f"{v['marca']} {v['modelo']} {v['año']} ({_km(v['kilometraje'])} km) a {_cop(v['precio'])}"
                              for v in carros)
            texto = f"Hola {nombre} 👋 Tenemos disponible: {lista}. ¿Quieres fotos o agendar la visita?"
        else:
            texto = (f"Hola {nombre}, en este momento no tenemos ese carro, pero te aviso apenas entre uno. "
                     "¿Me confirmas tu presupuesto y si lo quieres automático?")
        temp = "caliente" if (e["presupuesto"] and (e["urgente"] or e["marca"] or e["tipo"])) or i == "disponibilidad" else "tibio"
    elif i == "vender":
        texto = (f"Hola {nombre}, sí compramos carros y pagamos de contado. Cotiza en 30 segundos en "
                 "autonegocio-web.onrender.com/cotiza o envíame año, kilometraje y 4 fotos.")
        temp = "caliente" if e["urgente"] else "tibio"
    elif i == "financiacion":
        if e["ingreso"]:
            # cuota máxima ≈ 40 % del ingreso; a 72 meses y 19,5 % E.A. cada millón de cuota financia ~47 M
            tope = e["ingreso"] * 0.40 * 47
            texto = (f"Hola {nombre}, sí financiamos. Con ese ingreso podrías financiar hasta unos "
                     f"{_cop(round(tope, -6))} (sujeto a estudio). ¿Cuánto tienes de cuota inicial?")
            temp = "caliente"
        else:
            texto = (f"Hola {nombre}, sí financiamos con bancos aliados, desde el 10 % de cuota inicial y hasta "
                     "72 meses. ¿Cuál es tu ingreso mensual aproximado para precalificarte?")
    elif i == "cita":
        texto = (f"Hola {nombre}, estamos en Bogotá, de lunes a sábado de 8:00 a 6:00. "
                 "¿Qué día te queda bien para agendar tu visita o test drive?")
        temp = "tibio"
    else:
        humano, temp = True, "—"
        texto = f"Hola {nombre}, gracias por escribir. Un asesor te responde en un momento."
    return {"id": m["id"], "canal": m["canal"], "hora": m["hora"], "cliente": m["cliente"],
            "mensaje": m["texto"], **e, "respuesta": texto, "a_humano": humano, "temperatura": temp,
            "acierto": e["intencion"] == m["intencion_real"]}


def analizar(mensajes: list[dict], inventario: list[dict]) -> dict:
    res = [responder(m, inventario) for m in mensajes]
    auto = [r for r in res if not r["a_humano"]]
    fuera_horario = [r for r in res if not ("08:00" <= r["hora"] < "18:00")]
    calientes = [r for r in res if r["temperatura"] == "caliente"]
    por_intencion: dict[str, int] = {}
    for r in res:
        por_intencion[r["intencion"]] = por_intencion.get(r["intencion"], 0) + 1
    return {
        "mensajes": len(res),
        "precision_intencion_pct": round(sum(r["acierto"] for r in res) / len(res) * 100, 1),
        "resueltos_automaticamente": len(auto),
        "resueltos_pct": round(len(auto) / len(res) * 100, 1),
        "pasados_a_humano": len(res) - len(auto),
        "fuera_de_horario": len(fuera_horario),
        "leads_calientes": len(calientes),
        "por_intencion": por_intencion,
        "tiempo_respuesta": {"agente_min": 1, "asesor_min": RESPUESTA_HUMANO_MIN},
        "detalle": res,
        "recomendacion": (
            f"El agente respondió solo {len(auto)} de {len(res)} mensajes en menos de 1 minuto, "
            f"incluidos {len(fuera_horario)} que llegaron fuera del horario de atención. "
            f"Detectó {len(calientes)} leads calientes para que un asesor los llame primero y "
            f"pasó {len(res) - len(auto)} (quejas o mensajes dudosos) a una persona."
        ),
        "supuestos": f"Primera respuesta de un asesor: {RESPUESTA_HUMANO_MIN} minutos en promedio. "
                     "La precisión se mide contra mensajes simulados; con mensajes reales será menor "
                     "con palabras clave y mayor con Claude.",
    }
