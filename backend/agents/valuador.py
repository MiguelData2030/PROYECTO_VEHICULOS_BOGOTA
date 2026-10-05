"""
Agente Valuador — calculates fair market price for vehicles.

Responsibilities:
- Estimate fair market value using historical data and scoring
- Provide buy/sell price recommendations
- Generate detailed valuation reports
- Use Claude API for nuanced analysis when available
"""

import logging
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.database import AsyncSessionLocal
from backend.models.vehiculo import Vehiculo
from backend.scraping.scraper_manager import ScraperManager
from .base_agent import ask_claude

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres el Agente Valuador de AutoNegocio, experto en valuación de vehículos usados en Colombia.

Tu trabajo es analizar datos del mercado y proporcionar valuaciones precisas.

Factores de depreciación en Colombia:
- Toyota: retiene 75-80% a 3 años, 60-65% a 5 años
- Mazda: 70-75% a 3 años, 55-60% a 5 años
- Chevrolet: 65-70% a 3 años, 50-55% a 5 años
- Kia: 65-70% a 3 años, 50-55% a 5 años
- Renault: 60-65% a 3 años, 45-50% a 5 años

Variables que afectan precio:
- Transmisión automática vale 5-15% más
- Colores blanco/gris/negro tienen mejor reventa
- SUV retienen más valor que sedanes
- Kilometraje ideal: <15,000 km/año
- Bogotá tiene el mercado más líquido

Responde en español, con números concretos en COP."""


class AgenteValuador:
    """Provides intelligent vehicle valuation."""

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
    ) -> dict:
        """
        Generate a full valuation for a vehicle.

        Returns dict with:
        - precio_mercado_estimado: estimated market value
        - precio_compra_sugerido: suggested buy price
        - precio_venta_sugerido: suggested sell price
        - margen_estimado_pct: expected margin %
        - score: opportunity score 0-100
        - analisis: text analysis (from Claude or template)
        - datos_mercado: raw market data used
        """
        # Gather market data
        market_data = await self._get_market_data(marca, modelo, año)

        # Calculate opportunity score
        listing = {
            "marca": marca, "modelo": modelo, "año": año,
            "kilometraje": kilometraje, "transmision": transmision,
            "combustible": combustible, "color": color,
            "tipo_vehiculo": tipo_vehiculo, "ubicacion": ciudad,
        }
        score = ScraperManager.calculate_score(
            listing, market_data.get("precio_promedio")
        )

        # Calculate prices
        precio_mercado = market_data.get("precio_promedio")
        if precio_mercado:
            # Adjust for specific vehicle attributes
            ajuste = self._calculate_adjustments(
                kilometraje, año, transmision, color, tipo_vehiculo, estado_mecanico
            )
            precio_ajustado = int(precio_mercado * (1 + ajuste))
            precio_compra = int(precio_ajustado * 0.85)  # Buy at 15% below
            precio_venta = precio_ajustado
            margen_pct = round((precio_venta - precio_compra) / precio_compra * 100, 1)
        else:
            precio_ajustado = None
            precio_compra = None
            precio_venta = None
            margen_pct = None

        # Generate analysis
        analisis = await self._generate_analysis(
            marca, modelo, año, kilometraje, transmision, combustible,
            color, tipo_vehiculo, ciudad, estado_mecanico,
            market_data, precio_ajustado, score,
        )

        return {
            "precio_mercado_estimado": precio_ajustado,
            "precio_compra_sugerido": precio_compra,
            "precio_venta_sugerido": precio_venta,
            "margen_estimado_pct": margen_pct,
            "score": score,
            "analisis": analisis,
            "datos_mercado": market_data,
        }

    def _calculate_adjustments(
        self, km: int, año: int, trans: str, color: str, tipo: str, estado: str,
    ) -> float:
        """Return a percentage adjustment factor based on vehicle attributes."""
        ajuste = 0.0

        # Kilometraje adjustment
        edad = max(1, 2026 - año)
        km_por_año = km / edad
        if km_por_año < 10000:
            ajuste += 0.05
        elif km_por_año > 20000:
            ajuste -= 0.08

        # Transmission
        if "automatica" in trans.lower() or "automática" in trans.lower():
            ajuste += 0.05

        # Color
        colores_premium = {"blanco", "gris", "negro", "plata", "plateado"}
        if color.lower() in colores_premium:
            ajuste += 0.03

        # Type
        if tipo.lower() in ("suv", "camioneta"):
            ajuste += 0.03

        # Mechanical condition
        if estado.lower() == "excelente":
            ajuste += 0.05
        elif estado.lower() == "regular":
            ajuste -= 0.10

        return ajuste

    async def _get_market_data(self, marca: str, modelo: str, año: int) -> dict:
        """Fetch market reference data from the database."""
        async with AsyncSessionLocal() as session:
            # Exact match
            result = await session.execute(
                select(
                    func.avg(Vehiculo.precio_mercado).label("avg"),
                    func.min(Vehiculo.precio_mercado).label("min"),
                    func.max(Vehiculo.precio_mercado).label("max"),
                    func.count().label("count"),
                ).where(
                    Vehiculo.marca.ilike(marca),
                    Vehiculo.modelo.ilike(f"%{modelo}%"),
                    Vehiculo.año.between(año - 1, año + 1),
                    Vehiculo.precio_mercado.isnot(None),
                )
            )
            row = result.one()

            if row.count and row.count > 0:
                return {
                    "precio_promedio": int(row.avg),
                    "precio_min": int(row.min),
                    "precio_max": int(row.max),
                    "muestras": row.count,
                    "metodo": "exacto",
                }

            # Fallback: brand + year
            result = await session.execute(
                select(
                    func.avg(Vehiculo.precio_mercado).label("avg"),
                    func.min(Vehiculo.precio_mercado).label("min"),
                    func.max(Vehiculo.precio_mercado).label("max"),
                    func.count().label("count"),
                ).where(
                    Vehiculo.marca.ilike(marca),
                    Vehiculo.año.between(año - 1, año + 1),
                    Vehiculo.precio_mercado.isnot(None),
                )
            )
            row = result.one()

            if row.count and row.count > 0:
                return {
                    "precio_promedio": int(row.avg),
                    "precio_min": int(row.min),
                    "precio_max": int(row.max),
                    "muestras": row.count,
                    "metodo": "marca_año",
                }

            return {"precio_promedio": None, "muestras": 0, "metodo": "sin_datos"}

    async def _generate_analysis(
        self, marca, modelo, año, km, trans, comb, color, tipo, ciudad, estado,
        market_data, precio_ajustado, score,
    ) -> str:
        """Generate valuation analysis text."""
        prompt = f"""Genera una valuación concisa para este vehículo:

Vehículo: {marca} {modelo} {año}
Kilometraje: {km:,} km
Transmisión: {trans}
Combustible: {comb}
Color: {color}
Tipo: {tipo}
Ciudad: {ciudad}
Estado mecánico: {estado}

Datos del mercado:
- Precio promedio de referencia: ${market_data.get('precio_promedio', 'N/A')} COP
- Muestras: {market_data.get('muestras', 0)}
- Método: {market_data.get('metodo', 'N/A')}

Precio ajustado estimado: ${precio_ajustado:,} COP (si está disponible)
Score de oportunidad: {score}/100

Genera:
1. Valuación en 2-3 líneas con precio sugerido de compra y venta
2. Factores positivos y negativos (2-3 de cada uno)
3. Recomendación final: comprar o no, y a qué precio máximo"""

        response = ask_claude(prompt, system=SYSTEM_PROMPT, max_tokens=1000)
        if response:
            return response

        # Fallback template
        if not precio_ajustado:
            return (
                f"Sin suficientes datos de mercado para {marca} {modelo} {año}. "
                f"Se recomienda investigación manual de precios en TuCarro y Carroya."
            )

        precio_compra = int(precio_ajustado * 0.85)
        nivel = "Excelente" if score >= 75 else "Buena" if score >= 60 else "Regular"

        return (
            f"Valuación {marca} {modelo} {año}: "
            f"Precio estimado de mercado ${precio_ajustado:,.0f} COP. "
            f"Compra sugerida: ${precio_compra:,.0f} COP. "
            f"Score de oportunidad: {score}/100 ({nivel}). "
            f"Basado en {market_data.get('muestras', 0)} muestras del mercado."
        )
