"""
Agente de Marketing — the marketing manager of the dealership.

  estrategia(): reads social media results, the CRM and the inventory and
    decides where the money goes and what to publish:
      1. funnel and return per channel (reach → leads → sales → profit),
      2. next month's ad budget, moved toward the channels that sell,
      3. which cars to push this week, to whom and with which message,
      4. a weekly content calendar (network, format, day, hook),
      5. alerts (unanswered social leads, expensive channels, dead formats)
         and A/B tests to run.
  redactar(): the copywriting skill — marketplace title, catalogue
    description, Instagram post and WhatsApp message for one car.

Claude writes the strategy memo and the copy when available; otherwise the
agent uses its own rules and templates built from the real data.
"""

from __future__ import annotations

import logging
import re
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select

from backend.models import Publicacion, RedMetrica, Seguimiento, Transaccion, Vehiculo
from backend.models.database import AsyncSessionLocal
from .base_agent import ask_claude

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres el Agente de Marketing de AutoNegocio, compraventa de usados en Bogotá.
Escribes anuncios que venden: concretos, honestos y con los datos que el comprador colombiano
busca (año, kilometraje, transmisión, dueños, papeles al día, financiación, pico y placa).
Nunca inventes equipamiento, garantías ni datos que no estén en la ficha. Tono cercano y
profesional, español de Colombia."""

SECCIONES = ("TITULO", "DESCRIPCION", "INSTAGRAM", "WHATSAPP")

TRANS = {"automatica": "automática", "mecanica": "mecánica", "cvt": "automática CVT", "semiautomatica": "semiautomática"}


def _cop(v) -> str:
    return f"${v:,.0f}".replace(",", ".") if v else "precio a convenir"


def _km(v) -> str:
    return f"{v:,.0f}".replace(",", ".")


def _ficha(v: Vehiculo) -> str:
    docs = [n for n, ok in (("SOAT", v.soat_vigente), ("tecnomecánica", v.tecnicomecanica_vigente),
                            ("impuestos al día", v.impuestos_al_dia), ("libre de prendas", v.libre_prendas)) if ok]
    # Drop the photo credit line: it is not sales copy
    descripcion = re.sub(r"\s*Fotos referenciales.*$", "", v.descripcion or "").strip()
    return (
        f"{v.marca} {v.modelo} {v.año} · {v.tipo_vehiculo} · {_km(v.kilometraje)} km · "
        f"transmisión {TRANS.get(v.transmision, v.transmision)} · {v.combustible} · "
        f"{v.cilindraje or '?'} cc · color {v.color} · {v.num_dueños or '?'} dueño(s) · "
        f"estado mecánico {v.estado_mecanico or 'bueno'} · ciudad {v.ciudad} · precio {_cop(v.precio_venta)} · "
        f"documentos: {', '.join(docs) or 'por confirmar'} · notas: {descripcion or '-'}"
    )


class AgenteMarketing:
    async def estrategia(self, dias: int = 90, presupuesto: Optional[float] = None) -> dict:
        """Marketing plan for the next weeks, built from the business data."""
        return await _estrategia(dias, presupuesto)

    async def redactar(self, v: Vehiculo, whatsapp: Optional[str] = None) -> dict:
        texto = await ask_claude(
            f"""Ficha del vehículo:
{_ficha(v)}

Escribe exactamente estas 4 secciones, cada una precedida por su marcador en una línea aparte:
### TITULO
(máximo 60 caracteres, para TuCarro/Carroya)
### DESCRIPCION
(80-130 palabras para el catálogo web)
### INSTAGRAM
(post con 3-5 emojis y 8-12 hashtags relevantes de Bogotá/Colombia)
### WHATSAPP
(mensaje de 2-3 líneas para enviar a un cliente interesado)""",
            system=SYSTEM_PROMPT,
        )
        if texto:
            partes = self._parse(texto)
            if all(partes.get(s) for s in SECCIONES):
                return {**self._salida(partes), "analisis_ia": True}
            logger.warning("Respuesta de Claude sin las 4 secciones; se usa la plantilla")
        return {**self._plantilla(v), "analisis_ia": False}

    @staticmethod
    def _parse(texto: str) -> dict:
        partes: dict[str, str] = {}
        actual = None
        for linea in texto.splitlines():
            m = re.match(r"^\s*#+\s*(TITULO|TÍTULO|DESCRIPCION|DESCRIPCIÓN|INSTAGRAM|WHATSAPP)\s*$", linea, re.I)
            if m:
                actual = m.group(1).upper().replace("Í", "I").replace("Ó", "O")
                partes[actual] = ""
            elif actual:
                partes[actual] += linea + "\n"
        return {k: v.strip() for k, v in partes.items()}

    @staticmethod
    def _salida(p: dict) -> dict:
        return {
            "titulo": p["TITULO"][:80],
            "descripcion": p["DESCRIPCION"],
            "instagram": p["INSTAGRAM"],
            "whatsapp": p["WHATSAPP"],
        }

    def _plantilla(self, v: Vehiculo) -> dict:
        trans = TRANS.get(v.transmision, v.transmision)
        dueños = "único dueño" if v.num_dueños == 1 else None  # only a selling point when it's one
        docs = "papeles al día" if v.soat_vigente and v.impuestos_al_dia else None
        destacados = [x for x in (dueños, docs, "libre de prendas" if v.libre_prendas else None,
                                  "híbrido: sin pico y placa" if v.combustible == "hibrido" else None) if x]
        titulo = f"{v.marca} {v.modelo} {v.año} {trans} {_km(v.kilometraje)} km"[:60]
        descripcion = (
            f"{v.marca} {v.modelo} modelo {v.año} con {_km(v.kilometraje)} km, transmisión {trans}, "
            f"motor de {v.cilindraje or '?'} cc a {v.combustible} y color {v.color.lower()}. "
            + (f"{', '.join(destacados).capitalize()}. " if destacados else "")
            + f"Estado mecánico {v.estado_mecanico or 'bueno'}, revisado por nuestro equipo y con peritaje disponible. "
            f"Precio: {_cop(v.precio_venta)}. Recibimos tu carro en parte de pago y te ayudamos con la financiación. "
            f"Agenda tu visita en {v.ciudad}."
        )
        tag_marca = re.sub(r"[^a-z0-9]", "", v.marca.lower())
        tag_modelo = re.sub(r"[^a-z0-9]", "", v.modelo.lower().split()[0])
        instagram = (
            f"🚗 {v.marca} {v.modelo} {v.año}\n"
            f"📍 {v.ciudad} · {_km(v.kilometraje)} km · {trans}\n"
            + (f"✅ {' · '.join(destacados)}\n" if destacados else "")
            + f"💰 {_cop(v.precio_venta)} — financiamos y recibimos tu usado\n"
            f"📲 Escríbenos por WhatsApp\n\n"
            f"#{tag_marca} #{tag_marca}{tag_modelo} #carrosusados #carrosbogota #bogota #autosenventa "
            f"#vehiculosusados #colombia #{v.tipo_vehiculo.lower().replace('-', '')} #autonegocio"
        )
        whatsapp = (
            f"Hola 👋 Te comparto el {v.marca} {v.modelo} {v.año}: {_km(v.kilometraje)} km, {trans}"
            + (f", {destacados[0]}" if destacados else "")
            + f". Precio {_cop(v.precio_venta)}. ¿Te gustaría verlo esta semana o que te simule la financiación?"
        )
        return {"titulo": titulo, "descripcion": descripcion, "instagram": instagram, "whatsapp": whatsapp}


# ===========================================================================
# Estrategia — the marketing manager
# ===========================================================================

PAGADAS = ("instagram", "facebook", "tiktok")      # WhatsApp is where leads land, not an ad channel
RED_LABEL = {"instagram": "Instagram", "facebook": "Facebook", "tiktok": "TikTok", "whatsapp": "WhatsApp"}
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
# Usual best posting hour per network for Bogotá audiences (no hourly data in the system)
HORA = {"instagram": "19:00", "facebook": "12:30", "tiktok": "20:00", "whatsapp": "10:00"}
PIEZAS_SEMANA = 10
CAMBIO_MAX = 0.30          # never move a channel's budget more than ±30 % in one month
PRUEBA_PCT = 0.10          # budget share to test a channel that sells organically but has no ads

SEGMENTOS = {
    # segment → audience, key message, preferred networks
    "primer_carro": ("Primer carro: 22 a 34 años, estudiantes y recién empleados",
                     "cuota mensual baja y poco consumo", ("tiktok", "instagram")),
    "ejecutivo": ("Ejecutivos de 35 a 55 años con alto poder adquisitivo",
                  "estatus, bajo kilometraje y respaldo de la marca", ("instagram", "facebook")),
    "familia": ("Familias de 30 a 50 años en Bogotá y la Sabana",
                "espacio, seguridad y financiación a la medida", ("facebook", "instagram")),
    "ciudad": ("Profesionales de 25 a 45 años que se mueven a diario por la ciudad",
               "economía, comodidad y papeles al día", ("instagram", "facebook")),
    "trabajo": ("Independientes y empresas de 30 a 55 años",
                "carro de trabajo, capacidad de carga y financiación", ("facebook",)),
}

GANCHOS = {
    "reel": "Recorrido de 15 segundos por el {carro}: arranque, interior y tablero con el kilometraje real",
    "video": "“¿Cuánto cuesta tener un {carro}?” en 20 segundos: cuota, SOAT y consumo",
    "carrusel": "6 fotos del {carro} y una última lámina con la cuota desde {cuota} al mes",
    "historia": "Encuesta “¿Contado o financiado?” con el {carro} y botón directo a WhatsApp",
    "post": "Foto principal del {carro}, precio y “recibimos tu carro como parte de pago”",
}

SYSTEM_PROMPT_ESTRATEGIA = """Eres el gerente de marketing de AutoNegocio, compraventa de carros usados en Bogotá.
Piensas en ventas y margen, no en likes: cada peso de pauta tiene que traer leads que se conviertan.
Conoces Instagram, Facebook, TikTok y WhatsApp para el mercado colombiano. Responde en español,
en viñetas, máximo 220 palabras, con cifras en COP. Usa solo los datos que te doy."""


def _aware(d: datetime) -> datetime:
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _fecha(d) -> date:
    return d.date() if isinstance(d, datetime) else d


def _cuota(precio: float) -> float:
    """Monthly payment with 20 % down, 60 months at 19.5 % E.A. (same rules as the Agente de Crédito)."""
    i = 1.195 ** (1 / 12) - 1
    monto = precio * 0.8
    return monto * i / (1 - (1 + i) ** -60)


def _segmento(v: Vehiculo) -> str:
    tipo = (v.tipo_vehiculo or "").lower()
    precio = v.precio_venta or 0
    if tipo in ("pick-up", "camioneta"):
        return "trabajo"
    if precio >= 120_000_000:
        return "ejecutivo"
    if tipo == "hatchback" or precio < 50_000_000:
        return "primer_carro"
    if tipo == "suv":
        return "familia"
    return "ciudad"


def _engagement(filas: list[RedMetrica]) -> Optional[float]:
    alcance = sum(f.alcance for f in filas)
    return round(sum(f.interacciones for f in filas) / alcance * 100, 2) if alcance else None


async def _estrategia(dias: int, presupuesto: Optional[float]) -> dict:
    hoy = date.today()
    desde = hoy - timedelta(days=dias - 1)
    desde_pubs = hoy - timedelta(days=max(dias, 90) - 1)   # formats need a bigger sample
    limite = datetime.combine(desde, datetime.min.time(), tzinfo=timezone.utc)

    async with AsyncSessionLocal() as session:
        metricas = (await session.execute(
            select(RedMetrica).where(RedMetrica.fecha >= desde).order_by(RedMetrica.fecha))).scalars().all()
        pubs = (await session.execute(select(Publicacion).where(Publicacion.fecha >= desde_pubs))).scalars().all()
        segs = (await session.execute(select(Seguimiento))).scalars().all()
        stock = (await session.execute(select(Vehiculo).where(Vehiculo.estado == "disponible"))).scalars().all()
        ventas = (await session.execute(select(Transaccion).where(Transaccion.tipo == "venta"))).scalars().all()

    if not metricas:
        return {
            "sin_datos": True,
            "analisis": "Todavía no hay métricas de redes sociales. Carga la demo desde el Dashboard o registra "
                        "las métricas de Instagram, Facebook y TikTok para que el agente arme la estrategia.",
            "analisis_ia": False,
        }

    # ------------------------------------------------ profit per sale
    recientes = [t for t in ventas if (hoy - _fecha(t.fecha)).days <= 365 and t.ganancia_neta is not None]
    ganancia_venta = statistics.mean(t.ganancia_neta for t in recientes) if recientes else 8_000_000

    # ------------------------------------------------ 1. funnel per channel
    por_red: dict[str, list[RedMetrica]] = defaultdict(list)
    for m in metricas:
        por_red[m.red].append(m)
    crm = defaultdict(lambda: {"leads_crm": 0, "ventas": 0, "valor_ventas": 0.0})
    for s in segs:
        if s.canal in RED_LABEL and _aware(s.created_at) >= limite:
            crm[s.canal]["leads_crm"] += 1
            if s.etapa == "ganado":
                crm[s.canal]["ventas"] += 1
                crm[s.canal]["valor_ventas"] += s.valor_estimado or 0

    canales = []
    for red, filas in por_red.items():
        mitad = len(filas) // 2
        leads = sum(f.leads for f in filas)
        inversion = sum(f.inversion for f in filas)
        c = crm[red]
        n_ventas = c["ventas"]
        canales.append({
            "red": red,
            "nombre": RED_LABEL.get(red, red),
            "seguidores": filas[-1].seguidores,
            "crecimiento": filas[-1].seguidores - filas[0].seguidores,
            "alcance": sum(f.alcance for f in filas),
            "engagement_pct": _engagement(filas),
            "engagement_antes": _engagement(filas[:mitad]) if mitad else None,
            "engagement_despues": _engagement(filas[mitad:]) if mitad else None,
            "leads": leads,
            "inversion": inversion,
            "costo_por_lead": round(inversion / leads) if inversion and leads else None,
            "leads_crm": c["leads_crm"],
            "ventas": n_ventas,
            "valor_ventas": c["valor_ventas"],
            # lead → sale, on the same leads the cost per lead is measured on
            "conversion_pct": round(n_ventas / leads * 100, 1) if leads else None,
            "costo_por_venta": round(inversion / n_ventas, -3) if inversion and n_ventas else None,
            "ganancia_estimada": round(n_ventas * ganancia_venta, -3),
            "roi_pauta": round((n_ventas * ganancia_venta - inversion) / inversion, 1) if inversion else None,
        })
    canales.sort(key=lambda c: -c["ventas"])

    # ------------------------------------------------ 2. budget for next month
    factor_mes = 30 / dias
    actuales = {c["red"]: c["inversion"] * factor_mes for c in canales if c["red"] in PAGADAS}
    total = presupuesto if presupuesto else sum(actuales.values())
    eficiencia = {c["red"]: (c["ventas"] / c["inversion"] * 1_000_000 if c["inversion"] else 0)
                  for c in canales if c["red"] in PAGADAS}
    con_pauta = [r for r, v in actuales.items() if v > 0]
    media = statistics.mean(eficiencia[r] for r in con_pauta) if con_pauta else 0
    pesos: dict[str, float] = {}
    for r in con_pauta:
        rel = eficiencia[r] / media if media else 1
        pesos[r] = actuales[r] * max(1 - CAMBIO_MAX, min(1 + CAMBIO_MAX, rel ** 0.5))
    # A network that already brings leads or sales without ads gets a test budget
    con_leads = [c["leads"] for c in canales if c["red"] in PAGADAS and c["leads"]]
    umbral = statistics.median(con_leads) if con_leads else 0
    organicos = [c for c in canales if c["red"] in PAGADAS and not c["inversion"]
                 and (c["ventas"] or (c["leads"] and c["leads"] >= umbral))]
    prueba = max(organicos, key=lambda c: (c["ventas"], c["leads"])) if organicos else None
    suma = sum(pesos.values()) or 1
    bolsa = total * (1 - PRUEBA_PCT) if prueba else total
    asignado = {r: v / suma * bolsa for r, v in pesos.items()}
    if prueba:
        asignado[prueba["red"]] = total * PRUEBA_PCT
    leads_total = sum(c["leads"] for c in canales) or 1
    presupuesto_out = []
    for c in canales:
        if c["red"] not in PAGADAS:
            continue
        nuevo = round(asignado.get(c["red"], 0), -4)
        actual = round(actuales.get(c["red"], 0), -4)
        # an organic network has no cost per lead yet: assume the average of the paid ones
        pagados = [x for x in canales if x["costo_por_lead"]]
        cpl = c["costo_por_lead"] or (statistics.mean(x["costo_por_lead"] for x in pagados) if pagados
                                      else sum(actuales.values()) / leads_total)
        conv = (c["conversion_pct"] or 0) / 100
        leads_esp = nuevo / cpl if cpl and nuevo else 0
        if prueba and c["red"] == prueba["red"]:
            motivo = "prueba: ya trae clientes sin pauta"
        elif actual and nuevo > actual:
            motivo = "vende más por cada millón invertido"
        elif actual and nuevo < actual:
            motivo = "vende menos por cada millón invertido"
        else:
            motivo = "se mantiene"
        presupuesto_out.append({
            "red": c["red"], "nombre": c["nombre"], "actual": actual, "recomendado": nuevo,
            "cambio_pct": round((nuevo - actual) / actual * 100) if actual else None,
            "leads_esperados": round(leads_esp), "ventas_esperadas": round(leads_esp * conv, 1),
            "motivo": motivo,
        })

    # ------------------------------------------------ 3. formats and best days
    fmt = defaultdict(lambda: {"publicaciones": 0, "alcance": 0, "leads": 0})
    dia_red = defaultdict(lambda: [0, 0])          # (red, weekday) → [posts, leads]
    ultima_pub: dict[int, date] = {}
    for p in pubs:
        f = fmt[(p.red, p.tipo)]
        f["publicaciones"] += 1
        f["alcance"] += p.alcance
        f["leads"] += p.leads
        d = dia_red[(p.red, p.fecha.weekday())]
        d[0] += 1
        d[1] += p.leads
        if p.vehiculo_id:
            ultima_pub[p.vehiculo_id] = max(ultima_pub.get(p.vehiculo_id, p.fecha), p.fecha)
    formatos = sorted(
        ({"red": r, "nombre": RED_LABEL.get(r, r), "formato": t, **v,
          "leads_por_publicacion": round(v["leads"] / v["publicaciones"], 2),
          "alcance_por_publicacion": round(v["alcance"] / v["publicaciones"])}
         for (r, t), v in fmt.items()),
        key=lambda x: -x["leads_por_publicacion"],
    )
    mejor_formato: dict[str, str] = {}
    for f in formatos:                              # sorted best first
        mejor_formato.setdefault(f["red"], f["formato"])

    def mejores_dias(red: str) -> list[int]:
        prom = [(wd, v[1] / v[0]) for (r, wd), v in dia_red.items() if r == red and v[0]]
        return [wd for wd, _ in sorted(prom, key=lambda x: -x[1])] or [1, 3, 5]

    def leads_post(red: str) -> float:
        return next((f["leads_por_publicacion"] for f in formatos if f["red"] == red), 0)

    # ------------------------------------------------ 4. cars to push
    impulsar = []
    for v in stock:
        if not v.precio_venta:
            continue
        dias_stock = (hoy - _fecha(v.fecha_compra)).days if v.fecha_compra else 0
        margen = (v.precio_venta - v.precio_compra) / v.precio_compra * 100 if v.precio_compra else 0
        sin_pub = (hoy - ultima_pub[v.id]).days if v.id in ultima_pub else None
        prioridad = (0.5 * min(dias_stock / 60, 1) + 0.3 * min(max(margen, 0) / 20, 1)
                     + 0.2 * (1 if sin_pub is None or sin_pub > 14 else 0))
        publico, mensaje, redes_seg = SEGMENTOS[_segmento(v)]
        red = max(redes_seg, key=leads_post)
        razones = []
        if dias_stock > 45:
            razones.append(f"{dias_stock} días en inventario")
        if margen >= 15:
            razones.append(f"margen de {margen:.0f} %")
        if sin_pub is None:
            razones.append("nunca se ha publicado en redes")
        elif sin_pub > 14:
            razones.append(f"{sin_pub} días sin publicarse")
        impulsar.append({
            "vehiculo_id": v.id, "vehiculo": f"{v.marca} {v.modelo} {v.año}", "precio": v.precio_venta,
            "foto": (v.fotos or [None])[0], "dias_inventario": dias_stock, "margen_pct": round(margen, 1),
            "prioridad": round(prioridad * 100), "razones": razones or ["buena rotación esperada"],
            "publico": publico, "mensaje_clave": mensaje, "red": red, "red_nombre": RED_LABEL[red],
            "formato": mejor_formato.get(red, "reel"), "cuota_desde": round(_cuota(v.precio_venta), -3),
        })
    impulsar.sort(key=lambda x: -x["prioridad"])
    impulsar = impulsar[:6]

    # ------------------------------------------------ 5. weekly content calendar
    lead_share = {c["red"]: c["leads"] for c in canales if c["red"] in PAGADAS and c["leads"]}
    total_share = sum(lead_share.values()) or 1
    cupos = {r: max(1, round(PIEZAS_SEMANA * v / total_share)) for r, v in lead_share.items()}
    calendario = []
    usados: dict[int, int] = defaultdict(int)
    red_dia: set[tuple[str, int]] = set()
    for red, n in sorted(cupos.items(), key=lambda x: -x[1]):
        orden_dias = mejores_dias(red) + [d for d in range(7) if d not in mejores_dias(red)]
        preferidos = [c for c in impulsar if c["red"] == red] or impulsar
        for k in range(n):
            # the network's best days first, spreading the pieces across the week
            dia = min(orden_dias, key=lambda d: ((red, d) in red_dia, usados[d], orden_dias.index(d)))
            usados[dia] += 1
            red_dia.add((red, dia))
            carro = preferidos[k % len(preferidos)] if preferidos else None
            formato = mejor_formato.get(red, "reel")
            nombre = carro["vehiculo"] if carro else "carro de la semana"
            calendario.append({
                "dia": DIAS_SEMANA[dia], "orden": dia, "hora": HORA.get(red, "19:00"),
                "red": red, "red_nombre": RED_LABEL.get(red, red), "formato": formato,
                "vehiculo": nombre, "vehiculo_id": carro["vehiculo_id"] if carro else None,
                "objetivo": "leads" if formato in ("carrusel", "historia", "post") else "alcance y leads",
                "gancho": GANCHOS.get(formato, GANCHOS["post"]).format(
                    carro=nombre, cuota=_cop(carro["cuota_desde"]) if carro else "una cuota cómoda"),
            })
    calendario.sort(key=lambda c: (c["orden"], c["hora"]))

    # ------------------------------------------------ 6. alerts and A/B tests
    alertas = []
    ahora = datetime.now(timezone.utc)
    sin_atender = [s for s in segs if s.etapa == "nuevo" and s.canal in RED_LABEL
                   and (ahora - _aware(s.created_at)).days >= 1]
    if sin_atender:
        valor = sum((s.valor_estimado or 0) * 0.1 for s in sin_atender)
        alertas.append(f"{len(sin_atender)} leads de redes llevan más de 1 día sin respuesta "
                       f"({_cop(round(valor, -5))} en ventas ponderadas en riesgo): la pauta no sirve si nadie contesta.")
    cpls = [c["costo_por_lead"] for c in canales if c["costo_por_lead"]]
    if cpls:
        prom = statistics.mean(cpls)
        for c in canales:
            if c["costo_por_lead"] and c["costo_por_lead"] > prom * 1.4:
                alertas.append(f"{c['nombre']}: cada lead cuesta {_cop(c['costo_por_lead'])}, "
                               f"{c['costo_por_lead'] / prom:.1f} veces el promedio de las redes.")
    for c in canales:
        a, d = c["engagement_antes"], c["engagement_despues"]
        if a and d and d < a * 0.8:
            alertas.append(f"{c['nombre']}: el engagement cayó de {a:.1f} % a {d:.1f} % en el periodo; hay que renovar el contenido.")
    for f in formatos:
        if f["publicaciones"] >= 3 and f["leads"] == 0:
            alertas.append(f"{f['nombre']} {f['formato']}: {f['publicaciones']} publicaciones sin un solo lead; dejar de usarlo.")
    viejos = [c for c in impulsar if c["dias_inventario"] > 60]
    if viejos:
        alertas.append(f"{len(viejos)} carro(s) con más de 60 días en inventario: darles prioridad en la pauta "
                       "antes de que el Agente Financiero proponga rebajarlos.")

    pruebas = []
    if impulsar:
        c = impulsar[0]
        pruebas.append({"nombre": "Precio o cuota",
                        "a": f"Carrusel del {c['vehiculo']} mostrando el precio ({_cop(c['precio'])})",
                        "b": f"El mismo carrusel mostrando “desde {_cop(c['cuota_desde'])} al mes”",
                        "medir": "leads por cada 1.000 personas alcanzadas, 7 días, mismo presupuesto"})
    if formatos:
        f0 = formatos[0]
        pruebas.append({"nombre": "Con asesor o solo el carro",
                        "a": f"{f0['formato'].capitalize()} en {f0['nombre']} con un asesor presentando el carro",
                        "b": f"{f0['formato'].capitalize()} en {f0['nombre']} solo con tomas del carro y texto",
                        "medir": "mensajes a WhatsApp y costo por lead"})

    resultado = {
        "sin_datos": False,
        "dias": dias,
        "ganancia_por_venta": round(ganancia_venta, -3),
        "canales": canales,
        "presupuesto": {
            "total": round(total, -4), "por_red": presupuesto_out,
            "leads_esperados": sum(p["leads_esperados"] for p in presupuesto_out),
            "ventas_esperadas": round(sum(p["ventas_esperadas"] for p in presupuesto_out), 1),
            "canal_prueba": prueba["nombre"] if prueba else None,
        },
        "formatos": formatos[:8],
        "impulsar": impulsar,
        "calendario": calendario,
        "alertas": alertas,
        "pruebas_ab": pruebas,
        "supuestos": f"Ganancia neta promedio por venta {_cop(round(ganancia_venta, -3))} (ventas de los últimos 12 meses). "
                     f"El ajuste por eficiencia de cada red se limita a ±{CAMBIO_MAX * 100:.0f} % antes de repartir el total"
                     + (f"; el {PRUEBA_PCT * 100:.0f} % se reserva para probar una red que ya trae clientes sin pauta" if prueba else "")
                     + ". Horas de publicación: buenas prácticas para Bogotá (el sistema no guarda la hora de cada post).",
    }
    texto = await _estrategia_ia(resultado)
    resultado["analisis"] = texto or _estrategia_base(resultado)
    resultado["analisis_ia"] = texto is not None
    return resultado


def _estrategia_base(r: dict) -> str:
    lineas = []
    con_ventas = [c for c in r["canales"] if c["ventas"]]
    if con_ventas:
        mejor = con_ventas[0]
        lineas.append(f"{mejor['nombre']} es el canal que más vende: {mejor['ventas']} ventas en {r['dias']} días "
                      f"({_cop(mejor['valor_ventas'])}).")
    rentables = [c for c in r["canales"] if c["roi_pauta"] is not None]
    if rentables:
        top = max(rentables, key=lambda c: c["roi_pauta"])
        lineas.append(f"Cada peso de pauta en {top['nombre']} trajo {top['roi_pauta'] + 1:.1f} pesos de ganancia neta "
                      "en carros vendidos.")
    p = r["presupuesto"]
    cambios = [x for x in p["por_red"] if x["cambio_pct"]]
    if cambios or p["canal_prueba"]:
        lineas.append("Presupuesto del próximo mes: "
                      + "; ".join(f"{x['nombre']} {x['cambio_pct']:+d} %" for x in cambios)
                      + (f"; abrir pauta de prueba en {p['canal_prueba']} con el 10 %" if p["canal_prueba"] else "") + ".")
    lineas.append(f"Meta del mes con {_cop(p['total'])} de pauta: unos {p['leads_esperados']} leads y "
                  f"{p['ventas_esperadas']} ventas desde redes.")
    if r["impulsar"]:
        c = r["impulsar"][0]
        lineas.append(f"Carro a impulsar primero: {c['vehiculo']} ({', '.join(c['razones'])}), "
                      f"en {c['red_nombre']} con {c['formato']}, para {c['publico'][0].lower() + c['publico'][1:]}.")
    return "\n".join(f"• {x}" for x in lineas)


async def _estrategia_ia(r: dict) -> Optional[str]:
    canales = "\n".join(
        f"- {c['nombre']}: alcance {c['alcance']:,}, leads {c['leads']}, inversión {_cop(c['inversion'])}, "
        f"costo por lead {_cop(c['costo_por_lead']) if c['costo_por_lead'] else 'orgánico'}, ventas {c['ventas']}, "
        f"conversión {c['conversion_pct']} %, engagement {c['engagement_pct']} %"
        for c in r["canales"])
    pres = "; ".join(f"{x['nombre']}: {_cop(x['actual'])} → {_cop(x['recomendado'])}" for x in r["presupuesto"]["por_red"])
    carros = "\n".join(f"- {c['vehiculo']} ({_cop(c['precio'])}): {', '.join(c['razones'])}; público: {c['publico']}"
                       for c in r["impulsar"])
    formatos = ", ".join(f"{f['nombre']} {f['formato']} {f['leads_por_publicacion']} leads/post" for f in r["formatos"][:5])
    prompt = f"""Resultados de redes de AutoNegocio en los últimos {r['dias']} días:
{canales}
Ganancia neta promedio por carro vendido: {_cop(r['ganancia_por_venta'])}.
Formatos que más leads traen: {formatos}.
Presupuesto propuesto por el sistema: {pres}.
Carros a impulsar:
{carros}
Alertas: {r['alertas']}

Como gerente de marketing, da: (1) diagnóstico en 2 líneas, (2) el concepto de campaña del mes
con nombre y una frase, (3) las 3 movidas más importantes de este mes con cifras, (4) qué dejar de
hacer, (5) el indicador que revisarías cada lunes."""
    return await ask_claude(prompt, system=SYSTEM_PROMPT_ESTRATEGIA)
