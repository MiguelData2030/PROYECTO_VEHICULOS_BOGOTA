"""
Demo CRM pipeline and social media performance, consistent with the simulated
year built by generator.py (same clients, vehicles and sales).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

ASESORES = ["Andrea Gómez", "Felipe Rojas", "Gerencia"]
PROBABILIDAD = {"nuevo": 10, "contactado": 25, "cita": 45, "negociacion": 70, "ganado": 100, "perdido": 0}
MOTIVOS_PERDIDA = [
    "Compró en otro concesionario", "No le aprobaron el crédito", "El precio quedó fuera de su presupuesto",
    "Dejó de responder", "Buscaba un modelo más reciente", "Decidió esperar a la prima",
    "No le gustó el resultado del peritaje", "Encontró un particular más barato",
]
CANAL_LABEL = {
    "tucarro": "TuCarro", "instagram": "Instagram", "tiktok": "TikTok", "facebook": "Facebook",
    "whatsapp": "WhatsApp", "referido": "referido de un cliente", "vitrina": "la vitrina", "web": "la página web",
}
CANAL_POR_NOTA = {
    "TuCarro": "tucarro", "Instagram": "instagram", "Referido": "referido", "vitrina": "vitrina",
    "WhatsApp": "whatsapp",
}


@dataclass
class DemoSeguimiento:
    cliente_ref: str
    vehiculo_ref: Optional[str]
    tipo: str
    etapa: str
    canal: str
    valor_estimado: Optional[float]
    responsable: str
    creado: datetime
    proxima_accion: Optional[str] = None
    fecha_proxima: Optional[date] = None
    motivo_perdida: Optional[str] = None
    notas: Optional[str] = None
    interacciones: list = field(default_factory=list)  # (datetime, tipo, resumen)

    @property
    def probabilidad(self) -> int:
        return PROBABILIDAD[self.etapa]


BOGOTA = timezone(timedelta(hours=-5))


def _dt(d: date, hour: int) -> datetime:
    """Business-hours timestamp in Bogotá time (8 a.m. - 7 p.m.)."""
    return datetime.combine(d, time(min(max(hour, 8), 19), 0), tzinfo=BOGOTA)


def _canal(notas: str, rng) -> str:
    for key, canal in CANAL_POR_NOTA.items():
        if key in notas:
            return canal
    return rng.choice(["instagram", "facebook", "tiktok", "web"])


def _primer_contacto(canal: str, nombre_carro: str) -> tuple[str, str]:
    return {
        "instagram": ("mensaje_red", f"Escribió por DM de Instagram preguntando por el {nombre_carro}."),
        "facebook": ("mensaje_red", f"Comentó el anuncio de Facebook del {nombre_carro} y se le respondió por Messenger."),
        "tiktok": ("mensaje_red", f"Llegó por un video de TikTok del {nombre_carro}; pidió precio por mensaje."),
        "whatsapp": ("whatsapp", f"Escribió al WhatsApp desde la web interesado en el {nombre_carro}."),
        "web": ("email", f"Dejó sus datos en el formulario de la web por el {nombre_carro}."),
        "tucarro": ("llamada", f"Llamó desde el anuncio de TuCarro del {nombre_carro}."),
        "referido": ("llamada", f"Referido por un cliente anterior; busca algo como el {nombre_carro}."),
        "vitrina": ("visita", f"Pasó por la vitrina y vio el {nombre_carro}."),
    }[canal]


def construir_crm(b) -> list[DemoSeguimiento]:
    """`b` is the generator._Builder after build(): uses its rng, clients and vehicles."""
    rng, hoy = b.rng, b.today
    clientes = {c.ref: c for c in b.clientes}
    segs: list[DemoSeguimiento] = []

    def nombre(v) -> str:
        return f"{v.datos['marca']} {v.datos['modelo']} {v.datos['año']}"

    # 1) Won deals: every simulated sale has its commercial story
    for v in b.vehiculos:
        if not v.venta:
            continue
        cli = clientes[v.venta["cliente_ref"]]
        # Social channels gain weight month after month (content strategy at work)
        progreso = max(0.0, min(1.0, (v.venta["fecha"] - b.start).days / 365))
        pesos = {
            "tucarro": 30 - 15 * progreso, "instagram": 14 + 16 * progreso, "tiktok": 2 + 16 * progreso,
            "facebook": 10 - 2 * progreso, "whatsapp": 14, "referido": 16 - 6 * progreso, "vitrina": 14 - 8 * progreso,
        }
        canal = rng.choices(list(pesos), weights=list(pesos.values()))[0]
        cli.notas = f"[DEMO] Llegó por {CANAL_LABEL[canal]}."
        inicio = cli.creado or v.venta["fecha"] - timedelta(days=10)
        cierre = v.venta["fecha"]
        dias = max(1, (cierre - inicio).days)
        car = nombre(v)
        tipo1, txt1 = _primer_contacto(canal, car)
        pasos = [
            (inicio, tipo1, txt1),
            (inicio + timedelta(days=max(0, dias // 6)), "whatsapp", "Se enviaron fotos, ficha técnica y simulación de crédito."),
            (inicio + timedelta(days=max(1, dias // 3)), "visita", "Visitó la vitrina y revisó el carro."),
            (inicio + timedelta(days=max(1, dias // 3)), "test_drive", "Hizo test drive; le gustó el andar y el consumo."),
            (inicio + timedelta(days=max(1, (dias * 2) // 3)), "cotizacion",
             f"Cotización formal por ${v.venta['precio']:,.0f}.".replace(",", ".")),
            (cierre, "nota", "Negocio cerrado. " + v.venta["notas"].replace("[DEMO] ", "")),
        ]
        segs.append(DemoSeguimiento(
            cliente_ref=cli.ref, vehiculo_ref=v.ref, tipo="compra", etapa="ganado", canal=canal,
            valor_estimado=v.venta["precio"], responsable=rng.choice(ASESORES), creado=_dt(inicio, 10),
            notas="Cliente cerrado.",
            interacciones=[(_dt(d, 9 + i * 2), t, r) for i, (d, t, r) in enumerate(pasos)],
        ))

        # Realistic funnel: each sale usually had 1-3 other serious buyers who were lost
        for _ in range(rng.choices([0, 1, 2, 3, 4], [12, 30, 32, 16, 10])[0]):
            perdido = b.cliente("comprador", "Interesado que no cerró.", creado=inicio + timedelta(days=rng.randint(0, 5)))
            canal_p = rng.choice(["instagram", "facebook", "tiktok", "tucarro", "whatsapp"])
            t1, r1 = _primer_contacto(canal_p, car)
            motivo = rng.choice(MOTIVOS_PERDIDA)
            segs.append(DemoSeguimiento(
                cliente_ref=perdido.ref, vehiculo_ref=v.ref, tipo="compra", etapa="perdido", canal=canal_p,
                valor_estimado=v.datos["precio_venta"], responsable=rng.choice(ASESORES),
                creado=_dt(perdido.creado, 11), motivo_perdida=motivo,
                interacciones=[
                    (_dt(perdido.creado, 11), t1, r1),
                    (_dt(perdido.creado + timedelta(days=2), 15), "whatsapp", "Se le envió la ficha y el precio."),
                    (_dt(min(cierre, perdido.creado + timedelta(days=6)), 17), "nota", f"Perdido: {motivo.lower()}."),
                ],
            ))

    # 2) Active pipeline today, on the cars that are in stock
    en_stock = [v for v in b.vehiculos if not v.venta]
    etapas_activas = (["nuevo"] * 5 + ["contactado"] * 6 + ["cita"] * 5 + ["negociacion"] * 4)
    for i, etapa in enumerate(etapas_activas):
        v = en_stock[i % len(en_stock)]
        if v.datos["estado"] == "reservado" and etapa != "negociacion":
            etapa = "negociacion"
        canal = rng.choices(["instagram", "tiktok", "facebook", "whatsapp", "tucarro", "web", "referido"],
                            [26, 18, 12, 16, 14, 8, 6])[0]
        creado = hoy - timedelta(days=rng.randint(0, 3) if etapa == "nuevo" else rng.randint(2, 18))
        cli = b.cliente("comprador", f"Interesado en el {nombre(v)}.", creado=creado,
                        vehiculos_interes=[{"marca": v.datos["marca"], "modelo": v.datos["modelo"]}],
                        presupuesto_max=round(v.datos["precio_venta"] * rng.uniform(0.92, 1.08), -6))
        t1, r1 = _primer_contacto(canal, nombre(v))
        inter = [(_dt(creado, 10), t1, r1)]
        accion, plazo = "Primer contacto: enviar fotos y precio", 0
        if etapa in ("contactado", "cita", "negociacion"):
            inter.append((_dt(creado + timedelta(days=1), 12), "whatsapp", "Se enviaron fotos, ficha y simulación de crédito."))
            accion, plazo = "Llamar para agendar visita", rng.randint(-2, 2)
        if etapa in ("cita", "negociacion"):
            inter.append((_dt(creado + timedelta(days=2), 16), "visita", "Agendó visita a la vitrina."))
            accion, plazo = "Test drive agendado", rng.randint(0, 4)
        if etapa == "negociacion":
            inter.append((_dt(creado + timedelta(days=3), 11), "test_drive", "Hizo test drive."))
            inter.append((_dt(creado + timedelta(days=4), 15), "cotizacion", "Pidió descuento; se ofreció traspaso incluido."))
            accion, plazo = rng.choice([("Esperar respuesta del banco", 2), ("Enviar contraoferta final", 1),
                                        ("Firmar contrato y recibir abono", 3)])
        segs.append(DemoSeguimiento(
            cliente_ref=cli.ref, vehiculo_ref=v.ref, tipo="compra", etapa=etapa, canal=canal,
            valor_estimado=v.datos["precio_venta"], responsable=rng.choice(ASESORES), creado=_dt(creado, 9),
            proxima_accion=accion, fecha_proxima=hoy + timedelta(days=plazo), interacciones=inter,
        ))

    # 3) Sellers that want to sell us their car (from the website leads)
    for c in [c for c in b.clientes if c.tipo == "vendedor" and "Lead web" in c.notas]:
        etapa = rng.choice(["nuevo", "contactado", "cita", "negociacion"])
        oferta = (c.vehiculos_interes or [{}])[0]
        carro = f"{oferta.get('marca', '')} {oferta.get('modelo', '')} {oferta.get('anio', '')}".strip()
        inter = [(_dt(c.creado, 10), "email", f"Llenó el formulario Vender con su {carro}.")]
        accion = "Llamar y pedir fotos del carro"
        if etapa != "nuevo":
            inter.append((_dt(c.creado + timedelta(days=1), 11), "llamada", "Se pidieron fotos, kilometraje real y estado de papeles."))
            accion = "Agendar peritaje"
        if etapa in ("cita", "negociacion"):
            inter.append((_dt(c.creado + timedelta(days=3), 9), "visita", "Peritaje en sede: buen estado general."))
            accion = "Enviar oferta de compra"
        if etapa == "negociacion":
            inter.append((_dt(c.creado + timedelta(days=4), 16), "cotizacion", "Se ofertó con base en el Agente Valuador; pide un poco más."))
            accion = "Cerrar compra con contraoferta"
        segs.append(DemoSeguimiento(
            cliente_ref=c.ref, vehiculo_ref=None, tipo="venta", etapa=etapa, canal="web",
            valor_estimado=None, responsable="Gerencia", creado=_dt(c.creado, 9),
            proxima_accion=accion, fecha_proxima=hoy + timedelta(days=rng.randint(-1, 3)),
            notas=f"Quiere vender: {carro}.", interacciones=inter,
        ))
    return segs


# ---------------------------------------------------------------------------
# Social networks
# ---------------------------------------------------------------------------

REDES_BASE = {
    #            seguidores ini, fin, alcance diario base, leads/día, inversión diaria (COP)
    "instagram": (3_200, 7_400, 3_800, 1.6, 45_000),
    "facebook": (5_100, 6_000, 2_200, 0.8, 30_000),
    "tiktok": (900, 11_800, 6_500, 1.1, 0),
    "whatsapp": (1_150, 2_050, 900, 1.4, 0),
}


def construir_redes(b, dias: int = 90) -> tuple[list[dict], list[dict]]:
    rng, hoy = b.rng, b.today
    inicio = hoy - timedelta(days=dias - 1)
    metricas: list[dict] = []
    picos = {inicio + timedelta(days=d) for d in rng.sample(range(dias), 6)}  # viral posts
    for red, (seg_ini, seg_fin, alcance_base, leads_base, inversion) in REDES_BASE.items():
        salto = 0          # followers gained in viral jumps so far
        ruido = 0.0        # slow random walk so the curve is not perfectly smooth
        for d in range(dias):
            fecha = inicio + timedelta(days=d)
            progreso = d / (dias - 1)
            pico = fecha in picos and red in ("instagram", "tiktok")
            if pico:
                salto += rng.randint(250, 900) if red == "instagram" else rng.randint(600, 1800)
            ruido = max(-0.02, min(0.02, ruido + rng.uniform(-0.004, 0.004)))
            curva = progreso ** (1.6 if red == "tiktok" else 1.1)  # TikTok takes off later
            base = seg_ini + (seg_fin - seg_ini) * curva * (0.82 if red in ("instagram", "tiktok") else 1)
            seguidores = int((base + salto) * (1 + ruido))
            finde = fecha.weekday() >= 5
            alcance = int(alcance_base * (0.7 + 0.8 * progreso) * rng.uniform(0.7, 1.3)
                          * (1.25 if finde else 1) * (4.5 if pico else 1))
            tasa = {"instagram": 0.055, "facebook": 0.03, "tiktok": 0.075, "whatsapp": 0.12}[red]
            interacciones = int(alcance * tasa * rng.uniform(0.8, 1.2))
            mensajes = max(0, int(interacciones * rng.uniform(0.02, 0.05)) + (rng.randint(2, 8) if red == "whatsapp" else 0))
            leads = max(0, round(rng.gauss(leads_base * (0.6 + 0.8 * progreso), 0.9) + (3 if pico else 0)))
            metricas.append({
                "red": red, "fecha": fecha, "seguidores": seguidores, "alcance": alcance,
                "interacciones": interacciones, "mensajes": mensajes, "leads": leads,
                "inversion": float(inversion if (inversion and fecha.weekday() < 5) else 0),
            })

    publicaciones: list[dict] = []
    con_fotos = [v for v in b.vehiculos if v.datos["fotos"]]
    formatos = [
        ("instagram", "reel", "Walkaround {car}: lo que nadie te muestra"),
        ("instagram", "carrusel", "{car} — fotos reales, papeles al día"),
        ("instagram", "historia", "¡Recién llegado! {car}"),
        ("tiktok", "video", "¿Cuánto cuesta realmente un {car} usado en Bogotá?"),
        ("tiktok", "video", "3 cosas que revisar antes de comprar un {car}"),
        ("facebook", "post", "{car} disponible — financiamos y recibimos tu usado"),
        ("instagram", "post", "VENDIDO ✅ {car}. ¡Gracias por confiar en nosotros!"),
        ("whatsapp", "post", "Lista de difusión: novedades de la semana — {car}"),
    ]
    for i in range(48):
        red, tipo, plantilla = rng.choice(formatos)
        v = rng.choice(con_fotos)
        car = f"{v.datos['marca']} {v.datos['modelo']} {v.datos['año']}"
        fecha = inicio + timedelta(days=rng.randint(0, dias - 1))
        viral = fecha in picos or rng.random() < 0.07
        base = {"reel": 9_000, "video": 14_000, "carrusel": 4_500, "historia": 1_800, "post": 3_000}[tipo]
        if red == "whatsapp":
            base = 1_400
        alcance = int(base * rng.lognormvariate(0, 0.45) * (6 if viral else 1))
        me_gusta = int(alcance * rng.uniform(0.035, 0.08))
        publicaciones.append({
            "red": red, "tipo": tipo, "titulo": plantilla.format(car=car), "vehiculo_ref": v.ref,
            "fecha": fecha, "alcance": alcance, "me_gusta": me_gusta,
            "comentarios": int(me_gusta * rng.uniform(0.04, 0.12)),
            "compartidos": int(me_gusta * rng.uniform(0.02, 0.15 if red == "tiktok" else 0.06)),
            "guardados": int(me_gusta * rng.uniform(0.05, 0.2)),
            "mensajes": int(alcance * rng.uniform(0.001, 0.004)),
            "leads": max(0, int(alcance * rng.uniform(0.0003, 0.0012) * (1.5 if viral else 1))),
            "imagen": v.datos["fotos"][0],
        })
    publicaciones.sort(key=lambda p: p["fecha"], reverse=True)
    return metricas, publicaciones
