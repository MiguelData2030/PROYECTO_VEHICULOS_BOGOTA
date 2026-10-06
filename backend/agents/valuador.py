"""
Agente Valuador — fair price, buy limit and sale price for a used vehicle.

Data sources, in order of preference:
  1. Comparable listings collected by the Agente Cazador (oportunidades table):
     same brand and model, ±1-2 model years, prices adjusted for mileage.
  2. A depreciation model (new price 2026 × brand retention × age × mileage)
     when there are not enough comparables.
  3. AutoNegocio's own sales history for that model (days to sell, margin).

Business rules (business plan): buy 15-20 % below market, target ≥10 % net
margin after traspaso and reconditioning, "semáforo de oportunidad".
"""

from __future__ import annotations

import logging
import statistics
from datetime import date
from typing import Optional

from sqlalchemy import select

from backend.demo.generator import CATALOGO, RETENCION_MARCA
from backend.models import Oportunidad, Transaccion, Vehiculo
from backend.models.database import AsyncSessionLocal
from .base_agent import ask_claude

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres el Agente Valuador de AutoNegocio, compraventa de vehículos usados en Bogotá.
Eres un perito comercial experto en el mercado colombiano: conoces depreciación por marca,
liquidez por segmento, costos de traspaso y alistamiento, y cómo negociar con particulares.
Responde en español, directo y accionable, con cifras en COP. No repitas la tabla de datos:
interprétala. Máximo 180 palabras, en viñetas cortas."""

MARGEN_NETO_MINIMO = 0.10      # target net margin on the purchase price
NEGOCIACION_VENTA = 0.03       # typical discount granted when selling
LIQUIDEZ_ALTA = {"Toyota", "Mazda", "Chevrolet", "Renault", "Kia"}
COLORES_FACILES = {"blanco", "gris", "negro", "plata", "plateado", "blanco perla", "gris oscuro"}


def _round(value: float, step: int = 100_000) -> int:
    return int(round(value / step) * step)


def _precio_de_lista(value: float) -> int:
    """Retail-style price: 87.900.000 rather than 88.000.000."""
    return _round(value, 500_000) - 100_000


def _modelo_base(modelo: str) -> str:
    """'CX-5 Grand Touring' → 'cx-5'; 'Corolla Cross XEI' → 'corolla cross'; 'Land Cruiser Prado' → 'land cruiser'."""
    words = modelo.lower().split()
    if not words:
        return ""
    two_word = {"corolla", "land", "grand", "clase", "serie", "santa", "range"}
    if words[0] in two_word and len(words) > 1 and not words[1].isdigit():
        return f"{words[0]} {words[1]}"
    return words[0]


class AgenteValuador:
    """Provides data-driven vehicle valuation (with optional Claude analysis)."""

    async def valuate(
        self,
        marca: str,
        modelo: str,
        año: int,
        kilometraje: int,
        transmision: str = "automatica",
        combustible: str = "gasolina",
        color: str = "blanco",
        tipo_vehiculo: str = "SUV",
        ciudad: str = "Bogotá",
        estado_mecanico: str = "bueno",
        num_dueños: int = 1,
        precio_pedido: Optional[float] = None,
        url_anuncio: Optional[str] = None,
    ) -> dict:
        hoy = date.today()
        edad = max(0, hoy.year - año)

        # When valuing a market listing, never compare it with itself
        comparables = await self._comparables(marca, modelo, año, kilometraje, excluir_url=url_anuncio)
        historial = await self._historial(marca, modelo)

        # ---------------------------------------------------- fair market value
        if len(comparables) >= 3:
            ajustados = [c["precio_ajustado"] for c in comparables]
            valor = statistics.median(ajustados)
            q = statistics.quantiles(ajustados, n=4) if len(ajustados) >= 4 else [min(ajustados), valor, max(ajustados)]
            rango = (q[0], q[-1])
            metodo = f"{len(comparables)} anuncios comparables del mercado (ajustados por kilometraje)"
        else:
            valor = self._modelo_depreciacion(marca, modelo, año, kilometraje)
            rango = (valor * 0.92, valor * 1.08) if valor else (None, None)
            metodo = (
                "modelo de depreciación por marca, edad y kilometraje"
                + (f" (solo {len(comparables)} anuncios comparables)" if comparables else " (sin anuncios comparables)")
            )

        if not valor:
            return {
                "valor_mercado": None, "rango_mercado": [None, None],
                "precio_venta_sugerido": None, "precio_compra_ideal": None, "precio_compra_maximo": None,
                "costos_estimados": None, "margen_esperado_pct": None, "dias_estimados_venta": None,
                "liquidez": "desconocida", "semaforo": None, "veredicto": None,
                "factores_positivos": [], "factores_negativos": [],
                "comparables": comparables, "historial": historial, "metodo": metodo,
                "analisis": f"No hay datos suficientes para valuar un {marca} {modelo} {año}. "
                            "Ejecuta el Agente Cazador para traer anuncios del mercado o revisa TuCarro manualmente.",
                "analisis_ia": False,
            }

        # ------------------------------------------- vehicle-specific factors
        positivos: list[str] = []
        negativos: list[str] = []
        ajuste = 0.0
        km_año = kilometraje / max(1, edad)
        if km_año < 10_000:
            positivos.append(f"Kilometraje bajo ({km_año:,.0f} km/año)".replace(",", "."))
        elif km_año > 20_000:
            negativos.append(f"Kilometraje alto ({km_año:,.0f} km/año)".replace(",", "."))
        if estado_mecanico == "excelente":
            ajuste += 0.03
            positivos.append("Estado mecánico excelente")
        elif estado_mecanico == "regular":
            ajuste -= 0.08
            negativos.append("Estado mecánico regular: requiere taller antes de vender")
        if num_dueños == 1:
            positivos.append("Único dueño")
        elif num_dueños >= 3:
            ajuste -= 0.03
            negativos.append(f"{num_dueños} dueños anteriores")
        if color.lower() in COLORES_FACILES:
            positivos.append(f"Color {color.lower()}: de alta rotación")
        else:
            ajuste -= 0.02
            negativos.append(f"Color {color.lower()}: rota más lento")
        if "auto" in transmision.lower() or transmision.lower() == "cvt":
            positivos.append("Transmisión automática (más demandada en Bogotá)")
        elif tipo_vehiculo.lower() not in ("pick-up", "camioneta"):
            negativos.append("Transmisión mecánica: menos compradores en Bogotá")
        if combustible.lower() == "hibrido":
            positivos.append("Híbrido: exento de pico y placa en Bogotá")
        if marca in {"Toyota", "Mazda"}:
            positivos.append(f"{marca}: la marca que mejor retiene valor")
        if edad > 9:
            negativos.append(f"{edad} años: más difícil de financiar para el comprador")
        valor = valor * (1 + ajuste)

        # ---------------------------------------------------- business numbers
        costos = _round(650_000 + valor * 0.004 + valor * (0.035 if estado_mecanico == "regular" else 0.015), 50_000)
        venta = _precio_de_lista(valor)
        venta_neta = venta * (1 - NEGOCIACION_VENTA)
        compra_max = _round((venta_neta - costos) / (1 + MARGEN_NETO_MINIMO))
        compra_ideal = _round(min(compra_max, valor * 0.82))
        margen = (venta_neta - costos - compra_ideal) / compra_ideal * 100

        n = len(comparables)
        liquidez = "alta" if (n >= 12 or marca in LIQUIDEZ_ALTA and n >= 4) else "media" if n >= 4 or marca in LIQUIDEZ_ALTA else "baja"
        dias = historial["dias_promedio"] or {"alta": 20, "media": 35, "baja": 55}[liquidez]

        semaforo = veredicto = None
        if precio_pedido:
            if precio_pedido <= compra_ideal:
                semaforo = "verde"
                veredicto = f"COMPRAR: el precio pedido está {((valor - precio_pedido) / valor * 100):.0f}% bajo el mercado."
            elif precio_pedido <= compra_max:
                semaforo = "amarillo"
                veredicto = f"NEGOCIAR: ofrece {_round(compra_ideal, 500_000):,.0f} y no pases de {compra_max:,.0f}.".replace(",", ".")
            else:
                semaforo = "rojo"
                veredicto = f"NO COMPRAR a ese precio: supera el máximo rentable por {precio_pedido - compra_max:,.0f}.".replace(",", ".")

        resultado = {
            "valor_mercado": _round(valor),
            "rango_mercado": [_round(rango[0]) if rango[0] else None, _round(rango[1]) if rango[1] else None],
            "precio_venta_sugerido": venta,
            "precio_compra_ideal": compra_ideal,
            "precio_compra_maximo": compra_max,
            "costos_estimados": costos,
            "margen_esperado_pct": round(margen, 1),
            "dias_estimados_venta": round(dias),
            "liquidez": liquidez,
            "semaforo": semaforo,
            "veredicto": veredicto,
            "factores_positivos": positivos,
            "factores_negativos": negativos,
            "comparables": comparables[:8],
            "historial": historial,
            "metodo": metodo,
        }
        texto_ia = await self._analisis_ia(marca, modelo, año, kilometraje, transmision, color, estado_mecanico, precio_pedido, resultado)
        resultado["analisis"] = texto_ia or self._analisis_base(marca, modelo, año, resultado)
        resultado["analisis_ia"] = texto_ia is not None
        return resultado

    # ------------------------------------------------------------------ data
    async def valor_comparables(self, marca: str, modelo: str, año: int, km: int,
                                excluir_url: Optional[str] = None) -> tuple[Optional[float], int]:
        """Median comparable price (mileage/year adjusted) and sample size; None if < 3."""
        comps = await self._comparables(marca, modelo, año, km, excluir_url=excluir_url)
        if len(comps) < 3:
            return None, len(comps)
        return statistics.median(c["precio_ajustado"] for c in comps), len(comps)

    async def _comparables(self, marca: str, modelo: str, año: int, km: int,
                           excluir_url: Optional[str] = None) -> list[dict]:
        base = _modelo_base(modelo)
        async with AsyncSessionLocal() as session:
            for rango in (1, 2):
                rows = (await session.execute(
                    select(Oportunidad).where(
                        Oportunidad.marca.ilike(marca),
                        Oportunidad.modelo.ilike(f"%{base}%"),
                        Oportunidad.año.between(año - rango, año + rango),
                        Oportunidad.precio_publicado > 0,
                        *( [Oportunidad.url != excluir_url] if excluir_url else [] ),
                    )
                )).scalars().all()
                if len(rows) >= 3:
                    break

        if not rows:
            return []
        mediana = statistics.median(r.precio_publicado for r in rows)
        out = []
        for r in rows:
            # discard obvious outliers (typos, salvage, wrong category)
            if not (0.5 * mediana <= r.precio_publicado <= 2 * mediana):
                continue
            factor = 1.0
            if r.kilometraje and km:
                factor += max(-0.12, min(0.12, (r.kilometraje - km) / 10_000 * 0.008))
            factor += (año - r.año) * 0.06  # one model year ≈ 6 %
            out.append({
                "titulo": f"{r.marca} {r.modelo} {r.año}",
                "año": r.año,
                "kilometraje": r.kilometraje,
                "precio": r.precio_publicado,
                "precio_ajustado": r.precio_publicado * factor,
                "ubicacion": r.ubicacion,
                "plataforma": r.plataforma,
                "url": r.url,
            })
        out.sort(key=lambda c: (abs(c["año"] - año), abs((c["kilometraje"] or km) - km)))
        return out

    async def _historial(self, marca: str, modelo: str) -> dict:
        base = _modelo_base(modelo)
        async with AsyncSessionLocal() as session:
            rows = (await session.execute(
                select(Transaccion, Vehiculo)
                .join(Vehiculo, Transaccion.vehiculo_id == Vehiculo.id)
                .where(Transaccion.tipo == "venta", Vehiculo.marca.ilike(marca), Vehiculo.modelo.ilike(f"%{base}%"))
            )).all()
        dias, margenes, precios = [], [], []
        for tx, v in rows:
            precios.append(tx.precio)
            if v.fecha_compra:
                fv = tx.fecha.date() if hasattr(tx.fecha, "date") else tx.fecha
                fc = v.fecha_compra.date() if hasattr(v.fecha_compra, "date") else v.fecha_compra
                dias.append((fv - fc).days)
            if tx.ganancia_neta is not None and v.precio_compra:
                margenes.append(tx.ganancia_neta / v.precio_compra * 100)
        return {
            "ventas": len(rows),
            "precio_promedio": round(statistics.mean(precios)) if precios else None,
            "dias_promedio": round(statistics.mean(dias)) if dias else None,
            "margen_promedio_pct": round(statistics.mean(margenes), 1) if margenes else None,
        }

    def _modelo_depreciacion(self, marca: str, modelo: str, año: int, km: int) -> Optional[float]:
        base = _modelo_base(modelo)
        nuevo = next(
            (m[4] for m in CATALOGO if m[1].lower() == marca.lower() and base in m[2].lower()),
            None,
        )
        if not nuevo:
            return None
        edad = max(0, date.today().year - año)
        factor = 0.84 * (0.935 ** max(0, edad - 1)) if edad else 0.92
        factor *= RETENCION_MARCA.get(marca, 0.95)
        esperado = max(1, edad) * 13_000
        factor *= 1 - max(-0.06, min(0.15, (km - esperado) / esperado * 0.12))
        return nuevo * factor

    # -------------------------------------------------------------- analysis
    @staticmethod
    def _cop(v) -> str:
        return f"${v:,.0f}".replace(",", ".") if v else "N/D"

    def _analisis_base(self, marca, modelo, año, r: dict) -> str:
        c = self._cop
        partes = [
            f"{marca} {modelo} {año}: valor de mercado {c(r['valor_mercado'])} "
            f"(rango {c(r['rango_mercado'][0])} – {c(r['rango_mercado'][1])}), según {r['metodo']}.",
            f"Publícalo en {c(r['precio_venta_sugerido'])}. Paga idealmente {c(r['precio_compra_ideal'])} "
            f"y como máximo {c(r['precio_compra_maximo'])} para ganar al menos el 10% neto "
            f"después de {c(r['costos_estimados'])} en traspaso y alistamiento.",
            f"Liquidez {r['liquidez']}: se vendería en unos {r['dias_estimados_venta']} días.",
        ]
        h = r["historial"]
        if h["ventas"]:
            partes.append(f"Ya vendimos {h['ventas']} similares con margen promedio de {h['margen_promedio_pct']}%.")
        if r["veredicto"]:
            partes.append(r["veredicto"])
        return " ".join(partes)

    async def _analisis_ia(self, marca, modelo, año, km, trans, color, estado, precio_pedido, r: dict) -> Optional[str]:
        c = self._cop
        comps = "\n".join(
            f"- {x['titulo']}, {x['kilometraje'] or '?'} km: {c(x['precio'])} ({x['ubicacion'] or 'Bogotá'})"
            for x in r["comparables"][:6]
        ) or "- (sin comparables)"
        prompt = f"""Vehículo a valuar: {marca} {modelo} {año}, {km:,} km, {trans}, color {color}, estado {estado}.
Precio que pide el vendedor: {c(precio_pedido) if precio_pedido else 'no informado'}

Cálculo del sistema ({r['metodo']}):
- Valor de mercado: {c(r['valor_mercado'])} (rango {c(r['rango_mercado'][0])} – {c(r['rango_mercado'][1])})
- Precio de venta sugerido: {c(r['precio_venta_sugerido'])}
- Compra ideal: {c(r['precio_compra_ideal'])} · compra máxima rentable: {c(r['precio_compra_maximo'])}
- Costos estimados (traspaso + alistamiento): {c(r['costos_estimados'])}
- Liquidez: {r['liquidez']} · días estimados de venta: {r['dias_estimados_venta']}
- Historial propio: {r['historial']}
- A favor: {', '.join(r['factores_positivos']) or '-'}
- En contra: {', '.join(r['factores_negativos']) or '-'}
- Veredicto del sistema: {r['veredicto'] or '-'}

Anuncios comparables:
{comps}

Da: (1) tu lectura del precio, (2) qué revisar en el peritaje de este modelo en particular
(fallas típicas conocidas), (3) estrategia de negociación con el vendedor y (4) recomendación final."""
        return await ask_claude(prompt, system=SYSTEM_PROMPT)
