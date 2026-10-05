"""
Agente Cazador — monitors platforms 24/7 and detects buying opportunities.

Responsibilities:
- Trigger scraping runs on demand or via schedule
- Analyze scraped results and filter top opportunities
- Generate human-readable alerts for high-score vehicles
- Use Claude API to provide deeper analysis when available
"""

import logging
from typing import Optional

from backend.scraping.scraper_manager import ScraperManager, Oportunidad
from .base_agent import ask_claude

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres el Agente Cazador de AutoNegocio, una empresa de compra y venta de vehículos usados en Bogotá, Colombia.

Tu trabajo es analizar oportunidades de compra de vehículos y generar alertas claras para el equipo.

Contexto del negocio:
- Margen objetivo: 15-20% bruto
- Marcas prioritarias: Toyota, Mazda, Chevrolet, Kia, Renault, Hyundai
- Segmentos fuertes: SUV, Camioneta
- Zona: Bogotá y área metropolitana
- Precio promedio del inventario: $55M-150M COP

Responde siempre en español, de forma directa y accionable."""


class AgenteCazador:
    """Hunts for vehicle buying opportunities across platforms."""

    def __init__(self, filters: Optional[dict] = None):
        self.manager = ScraperManager(filters=filters)
        self.min_score = 60  # Minimum score to consider an opportunity

    async def hunt(self) -> list[Oportunidad]:
        """
        Run a full scraping cycle and return scored opportunities.
        """
        logger.info("Agente Cazador: starting hunt...")
        oportunidades = await self.manager.run()

        # Filter by minimum score
        good = [op for op in oportunidades if op.score >= self.min_score]
        logger.info(
            "Agente Cazador: %d/%d opportunities above score %d",
            len(good), len(oportunidades), self.min_score,
        )
        return good

    def generate_alert(self, oportunidades: list[Oportunidad]) -> str:
        """
        Generate a human-readable alert for the top opportunities.
        Uses Claude API if available, otherwise uses template.
        """
        if not oportunidades:
            return "No se encontraron oportunidades relevantes en este escaneo."

        top5 = oportunidades[:5]

        # Build context for Claude
        listings_text = "\n".join(
            f"- {op.listing.get('marca')} {op.listing.get('modelo')} {op.listing.get('año')} | "
            f"Precio: ${op.listing.get('precio', 0):,.0f} COP | "
            f"Mercado: ${op.market_price:,.0f} COP | " if op.market_price else ""
            f"Score: {op.score}/100 | "
            f"Descuento: {op.discount_pct:.1f}% | " if op.discount_pct else ""
            f"Fuente: {op.listing.get('plataforma', '?')}"
            for op in top5
        )

        prompt = f"""Analiza estas {len(top5)} oportunidades de compra de vehículos y genera un reporte ejecutivo breve.

Oportunidades encontradas:
{listings_text}

Total escaneado: {len(oportunidades)} oportunidades con score >= {self.min_score}

Genera:
1. Un resumen de 2-3 líneas
2. Para cada vehículo: por qué es buena oportunidad y riesgo principal
3. Recomendación: cuál comprar primero y por qué"""

        # Try Claude API
        response = ask_claude(prompt, system=SYSTEM_PROMPT, max_tokens=1500)
        if response:
            return response

        # Fallback: template-based alert
        lines = [f"🔍 ALERTA CAZADOR — {len(oportunidades)} oportunidades encontradas\n"]
        for i, op in enumerate(top5, 1):
            l = op.listing
            lines.append(
                f"{i}. {l.get('marca')} {l.get('modelo')} {l.get('año')} "
                f"— ${l.get('precio', 0):,.0f} COP "
                f"(Score: {op.score}/100)"
            )
            if op.discount_pct:
                lines.append(f"   Descuento vs mercado: {op.discount_pct:.1f}%")
            lines.append(f"   Fuente: {l.get('plataforma', '?')} | {l.get('url', '')}")
            lines.append("")

        return "\n".join(lines)

    async def run_and_alert(self) -> str:
        """Full cycle: hunt + generate alert."""
        oportunidades = await self.hunt()
        return self.generate_alert(oportunidades)
