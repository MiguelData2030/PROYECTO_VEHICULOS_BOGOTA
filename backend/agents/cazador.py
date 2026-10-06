"""
Agente Cazador — finds the best buying opportunities in the market.

- Optionally runs a fresh scan of TuCarro (ScraperManager) — ~30-60 s.
- Ranks the open opportunities stored in the DB by score and computes the
  real profit potential of each one (market price minus negotiation,
  traspaso and reconditioning).
- Writes a prioritised call list (Claude when available, rules otherwise).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select

from backend.models import Oportunidad
from backend.models.database import AsyncSessionLocal, ensure_tables
from backend.scraping.scraper_manager import ScraperManager
from .base_agent import ask_claude
from .valuador import AgenteValuador

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres el Agente Cazador de AutoNegocio, compraventa de usados en Bogotá.
Eres un comprador profesional: detectas gangas reales, descartas trampas (precios irreales,
anuncios gancho, vehículos con prenda, siniestros) y priorizas por rentabilidad y rotación.
Contexto: margen objetivo 15-20 % bruto, marcas prioritarias Toyota, Mazda, Chevrolet, Kia,
Renault, Hyundai; SUV y camionetas rotan más rápido. Responde en español, directo, máximo
200 palabras, en viñetas."""

ESTADOS_ABIERTOS = ("nueva", "contactada", "negociando")


def _costos(precio: float) -> float:
    return 650_000 + precio * 0.004 + precio * 0.015


class AgenteCazador:
    """Hunts for vehicle buying opportunities."""

    def __init__(self, filters: Optional[dict] = None, min_score: float = 60):
        self.filters = filters or {}
        self.min_score = min_score

    async def analizar(self, escanear: bool = False, limite: int = 10) -> dict:
        await ensure_tables()
        escaneados = None
        if escanear:
            scan_filters = {k: v for k, v in self.filters.items() if k in ("marca", "precio_max", "max_pages")}
            resultados = await ScraperManager(filters=scan_filters).run()
            escaneados = len(resultados)

        async with AsyncSessionLocal() as session:
            conds = [Oportunidad.estado.in_(ESTADOS_ABIERTOS), Oportunidad.score >= self.min_score]
            if self.filters.get("marca"):
                conds.append(Oportunidad.marca.ilike(self.filters["marca"]))
            if self.filters.get("precio_max"):
                conds.append(Oportunidad.precio_publicado <= self.filters["precio_max"])
            rows = (await session.execute(
                select(Oportunidad).where(*conds).order_by(Oportunidad.score.desc()).limit(limite)
            )).scalars().all()
            total_mercado = (await session.execute(select(func.count(Oportunidad.id)))).scalar_one()
            ultima = (await session.execute(select(func.max(Oportunidad.detectada_en)))).scalar_one()

        # Same market valuation as the Agente Valuador (comparables excluding the
        # listing itself) so both agents always agree on the numbers.
        valuador = AgenteValuador()
        oportunidades = []
        for o in rows:
            mercado, muestras = await valuador.valor_comparables(
                o.marca, o.modelo, o.año, o.kilometraje or 0, excluir_url=o.url
            )
            fuente = f"{muestras} comparables"
            if mercado is None:
                mercado, fuente = o.precio_mercado_estimado, "estimación del escaneo"
            ganancia = margen = descuento = None
            if mercado:
                ganancia = mercado * 0.97 - o.precio_publicado - _costos(o.precio_publicado)
                margen = ganancia / o.precio_publicado * 100
                descuento = (mercado - o.precio_publicado) / mercado * 100
            oportunidades.append({
                "id": o.id,
                "titulo": f"{o.marca} {o.modelo} {o.año}",
                "kilometraje": o.kilometraje,
                "ubicacion": o.ubicacion,
                "precio": o.precio_publicado,
                "precio_mercado": round(mercado, -5) if mercado else None,
                "fuente_mercado": fuente,
                "descuento_pct": round(descuento, 1) if descuento is not None else None,
                "ganancia_potencial": round(ganancia, -4) if ganancia is not None else None,
                "margen_potencial_pct": round(margen, 1) if margen is not None else None,
                "score": o.score,
                "estado": o.estado,
                "url": o.url,
                "plataforma": o.plataforma,
            })
        # Most profitable first
        oportunidades.sort(key=lambda x: x["margen_potencial_pct"] if x["margen_potencial_pct"] is not None else -99, reverse=True)

        texto = await self._resumen_ia(oportunidades, total_mercado)
        return {
            "escaneados": escaneados,
            "total_mercado": total_mercado,
            "ultima_actualizacion": ultima.isoformat() if isinstance(ultima, datetime) else None,
            "oportunidades": oportunidades,
            "resumen": texto or self._resumen_base(oportunidades, total_mercado),
            "analisis_ia": texto is not None,
        }

    # --------------------------------------------------------------- texts
    @staticmethod
    def _cop(v) -> str:
        return f"${v:,.0f}".replace(",", ".") if v else "N/D"

    def _resumen_base(self, ops: list[dict], total: int) -> str:
        if not ops:
            return (f"De {total} anuncios analizados, ninguno supera el score {self.min_score:.0f}. "
                    "Baja el score mínimo o ejecuta un escaneo nuevo.")
        c = self._cop
        rentables = [o for o in ops if (o["margen_potencial_pct"] or 0) >= 10]
        lineas = [f"De {total} anuncios del mercado, {len(ops)} superan el score {self.min_score:.0f}; "
                  f"{len(rentables)} dejarían más del 10% neto. Prioridad de llamadas:"]
        orden = [o for o in ops if (o["margen_potencial_pct"] or 0) > 0]
        descartadas = [o for o in ops if o not in orden]
        for i, o in enumerate(orden[:5], 1):
            extra = f", ganancia potencial {c(o['ganancia_potencial'])} ({o['margen_potencial_pct']}%)" if o["ganancia_potencial"] else ""
            lineas.append(f"{i}. {o['titulo']} en {c(o['precio'])} — {o['descuento_pct'] or 0:.0f}% bajo mercado{extra}.")
        if descartadas:
            lineas.append("Descartadas al precio pedido (no dejan margen): "
                          + ", ".join(o["titulo"] for o in descartadas) + ".")
        lineas.append("Antes de ofertar: verifica RUNT (prendas, comparendos), peritaje y que el precio no sea un anuncio gancho.")
        return "\n".join(lineas)

    async def _resumen_ia(self, ops: list[dict], total: int) -> Optional[str]:
        if not ops:
            return None
        c = self._cop
        listado = "\n".join(
            f"- {o['titulo']}, {o['kilometraje'] or '?'} km, {o['ubicacion'] or '?'}: pide {c(o['precio'])}, "
            f"mercado {c(o['precio_mercado'])}, {o['descuento_pct'] or 0:.0f}% bajo mercado, "
            f"ganancia potencial {c(o['ganancia_potencial'])} ({o['margen_potencial_pct']}%), score {o['score']:.0f}"
            for o in ops
        )
        prompt = f"""El sistema analizó {total} anuncios de TuCarro en Bogotá. Mejores oportunidades:
{listado}

Da: (1) resumen en 2 líneas, (2) orden de llamadas con una razón por vehículo,
(3) señales de alerta a verificar en los que parecen demasiado baratos,
(4) cuál comprarías hoy y hasta qué precio."""
        return await ask_claude(prompt, system=SYSTEM_PROMPT)

    # Backwards compatibility with the scheduler-era API
    async def run_and_alert(self) -> str:
        resultado = await self.analizar(escanear=True)
        return resultado["resumen"]
