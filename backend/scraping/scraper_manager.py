"""
ScraperManager — orchestrates all platform scrapers concurrently.

Responsibilities:
- Run TuCarroScraper and CarroyaScraper in parallel (asyncio.gather)
- Deduplicate results by URL
- Persist new listings to the DB as Oportunidad records
- Calculate opportunity score for each listing
- Estimate market prices from comparable listings already collected (oportunidades)
- Log all major steps
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.database import AsyncSessionLocal
from ..models.oportunidad import Oportunidad as OportunidadDB
from .carroya_scraper import CarroyaScraper
from .tucarro_scraper import TuCarroScraper

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Opportunity scoring constants (mirrors the spec exactly)
# ---------------------------------------------------------------------------
BRAND_SCORE: dict[str, int] = {
    "toyota":     15,
    "mazda":      15,
    "chevrolet":  10,
    "kia":        10,
    "renault":    10,
    "hyundai":    7,
    "nissan":     7,
    "ford":       7,
}
TIPO_SCORE: dict[str, int] = {
    "suv":       10,
    "camioneta": 8,
    "sedan":     5,
}
POPULAR_COLORS = {"blanco", "gris", "negro", "plata", "plateado", "silver"}
CURRENT_YEAR = 2026


# ---------------------------------------------------------------------------
# Oportunidad — lightweight dataclass (no SQLAlchemy model required yet)
# ---------------------------------------------------------------------------

class Oportunidad:
    """
    Represents a scraped listing enriched with opportunity score.
    Persisted in the `oportunidades` table (never in `vehiculos`, which is
    our own inventory and feeds the public catalogue).
    """

    def __init__(self, listing: dict, score: float, market_price: Optional[int]) -> None:
        self.listing = listing
        self.score = score
        self.market_price = market_price
        self.discount_pct: Optional[float] = None
        precio = listing.get("precio")
        if market_price and precio and market_price > 0:
            self.discount_pct = (market_price - precio) / market_price * 100

    def __repr__(self) -> str:
        return (
            f"<Oportunidad {self.listing.get('marca')} {self.listing.get('modelo')} "
            f"{self.listing.get('año')} | score={self.score:.1f} | "
            f"precio={self.listing.get('precio')}>"
        )


# ---------------------------------------------------------------------------
# ScraperManager
# ---------------------------------------------------------------------------

class ScraperManager:
    """Orchestrates all scrapers and persists results."""

    def __init__(self, filters: Optional[dict] = None) -> None:
        """
        Parameters
        ----------
        filters : dict, optional
            Keyword arguments forwarded to every scraper's scrape() method.
            Supported keys: marca, precio_min, precio_max, año_min, año_max,
            max_pages.
        """
        self.filters: dict = filters or {}
        self.logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self) -> list[Oportunidad]:
        """
        Run all scrapers concurrently, deduplicate, score, and save.

        Returns the list of Oportunidad objects sorted by score descending.
        """
        self.logger.info("ScraperManager starting | filters=%s", self.filters)
        start = datetime.now(tz=timezone.utc)

        # --- Run scrapers concurrently ---
        tucarro_task = asyncio.create_task(self._run_scraper("tucarro"))
        carroya_task = asyncio.create_task(self._run_scraper("carroya"))

        results = await asyncio.gather(tucarro_task, carroya_task, return_exceptions=True)

        all_listings: list[dict] = []
        for i, result in enumerate(results):
            platform = ("tucarro", "carroya")[i]
            if isinstance(result, Exception):
                self.logger.error("Scraper '%s' raised an exception: %s", platform, result)
            elif isinstance(result, list):
                self.logger.info("Scraper '%s' returned %d listings", platform, len(result))
                all_listings.extend(result)
            else:
                self.logger.warning("Scraper '%s' returned unexpected type: %s", platform, type(result))

        # --- Deduplicate by URL ---
        unique_listings = self._deduplicate(all_listings)
        self.logger.info(
            "After deduplication: %d unique listings (from %d total)",
            len(unique_listings), len(all_listings),
        )

        # --- Score and persist ---
        oportunidades: list[Oportunidad] = []
        async with AsyncSessionLocal() as session:
            for listing in unique_listings:
                try:
                    market_price = await self._get_market_price(
                        session,
                        listing.get("marca"),
                        listing.get("modelo"),
                        listing.get("año"),
                    )
                    score = self.calculate_score(listing, market_price)
                    op = Oportunidad(listing, score, market_price)
                    oportunidades.append(op)
                    await self._save_listing(session, listing, score, market_price)
                except Exception as exc:
                    self.logger.error(
                        "Error processing listing %s: %s",
                        listing.get("url", "?"), exc,
                    )
            try:
                await session.commit()
                self.logger.info("DB commit successful")
            except Exception as exc:
                await session.rollback()
                self.logger.error("DB commit failed: %s", exc)

        oportunidades.sort(key=lambda o: o.score, reverse=True)

        elapsed = (datetime.now(tz=timezone.utc) - start).total_seconds()
        self.logger.info(
            "ScraperManager done: %d opportunities scored in %.1fs",
            len(oportunidades), elapsed,
        )
        return oportunidades

    # ------------------------------------------------------------------
    # Internal: run individual scraper
    # ------------------------------------------------------------------

    async def _run_scraper(self, platform: str) -> list[dict]:
        """Instantiate and run the specified platform scraper."""
        if platform == "tucarro":
            scraper_cls = TuCarroScraper
        elif platform == "carroya":
            scraper_cls = CarroyaScraper
        else:
            raise ValueError(f"Unknown platform: {platform}")

        async with scraper_cls() as scraper:
            try:
                listings = await scraper.scrape(**dict(self.filters))
                return listings
            except Exception as exc:
                self.logger.error("Scraper '%s' failed: %s", platform, exc)
                raise

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    @staticmethod
    def _deduplicate(listings: list[dict]) -> list[dict]:
        """Remove duplicate listings by URL. First occurrence wins."""
        seen: set[str] = set()
        unique: list[dict] = []
        for listing in listings:
            url = listing.get("url") or ""
            if not url:
                # No URL → include anyway (can't deduplicate)
                unique.append(listing)
                continue
            if url not in seen:
                seen.add(url)
                unique.append(listing)
        return unique

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_score(listing: dict, market_price: Optional[int]) -> float:
        """
        Calculate an opportunity score 0-100 for a listing.

        Higher = better buying opportunity.
        """
        score: float = 0.0

        marca = (listing.get("marca") or "").lower()
        tipo = (listing.get("tipo_vehiculo") or "").lower()
        año = listing.get("año") or 0
        precio = listing.get("precio") or 0
        kilometraje = listing.get("kilometraje") or 0
        transmision = (listing.get("transmision") or "").lower()
        color = (listing.get("color") or "").lower()
        ubicacion = (listing.get("ubicacion") or "").lower()

        # --- Price discount vs market (max 40 points) ---
        if market_price and precio and precio < market_price:
            discount_ratio = (market_price - precio) / market_price * 100
            score += min(40.0, discount_ratio)

        # --- Brand popularity (max 15 points) ---
        score += BRAND_SCORE.get(marca, 0)

        # --- Vehicle type (max 10 points) ---
        for tipo_key, tipo_pts in TIPO_SCORE.items():
            if tipo_key in tipo:
                score += tipo_pts
                break

        # --- Age (max 10 points) — newer is better ---
        if año:
            age = CURRENT_YEAR - int(año)
            score += max(0, 10 - age)

        # --- Kilometraje (max 10 points) — lower per-year is better ---
        if año and kilometraje:
            age = max(1, CURRENT_YEAR - int(año))
            km_per_year = int(kilometraje) / age
            if km_per_year < 12_000:
                score += 10
            elif km_per_year < 18_000:
                score += 5

        # --- Transmission (max 5 points) ---
        if "automatica" in transmision or "automática" in transmision or "automatico" in transmision:
            score += 5

        # --- Color (max 5 points) ---
        if any(c in color for c in POPULAR_COLORS):
            score += 5

        # --- Location (max 5 points) ---
        if "bogot" in ubicacion:
            score += 5

        return round(min(score, 100.0), 2)

    # ------------------------------------------------------------------
    # Market price lookup
    # ------------------------------------------------------------------

    async def _get_market_price(
        self,
        session: AsyncSession,
        marca: Optional[str],
        modelo: Optional[str],
        año: Optional[int],
    ) -> Optional[int]:
        """
        Return the average asking price of comparable listings already
        collected in the oportunidades table for marca/modelo/año.

        Falls back to brand+year average, then brand average.
        """
        if not marca:
            return None

        # Exact match: marca + modelo + año
        if marca and modelo and año:
            result = await session.execute(
                select(func.avg(OportunidadDB.precio_publicado)).where(
                    OportunidadDB.marca.ilike(marca),
                    OportunidadDB.modelo.ilike(modelo),
                    OportunidadDB.año == int(año),
                    OportunidadDB.precio_publicado.isnot(None),
                )
            )
            avg = result.scalar()
            if avg:
                self.logger.debug(
                    "Market price for %s %s %s: %.0f COP (exact match)",
                    marca, modelo, año, avg,
                )
                return int(avg)

        # Fallback: marca + año ± 1 year
        if marca and año:
            result = await session.execute(
                select(func.avg(OportunidadDB.precio_publicado)).where(
                    OportunidadDB.marca.ilike(marca),
                    OportunidadDB.año.between(int(año) - 1, int(año) + 1),
                    OportunidadDB.precio_publicado.isnot(None),
                )
            )
            avg = result.scalar()
            if avg:
                self.logger.debug(
                    "Market price for %s %s: %.0f COP (year ±1 fallback)",
                    marca, año, avg,
                )
                return int(avg)

        # Last resort: brand average
        if marca:
            result = await session.execute(
                select(func.avg(OportunidadDB.precio_publicado)).where(
                    OportunidadDB.marca.ilike(marca),
                    OportunidadDB.precio_publicado.isnot(None),
                )
            )
            avg = result.scalar()
            if avg:
                self.logger.debug(
                    "Market price for %s: %.0f COP (brand average fallback)",
                    marca, avg,
                )
                return int(avg)

        return None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def _save_listing(
        self,
        session: AsyncSession,
        listing: dict,
        score: float,
        market_price: Optional[int],
    ) -> None:
        """
        Upsert a scraped listing into the oportunidades table (keyed by URL).

        Existing rows get fresh price/score data but keep their workflow
        state (estado, notas) so the team's follow-up is not lost.
        """
        url = listing.get("url")
        precio = listing.get("precio")
        año = listing.get("año")
        marca = listing.get("marca")
        if not (url and precio and año and marca):
            return  # not enough data to be actionable

        kilometraje = listing.get("kilometraje")
        descuento = None
        if market_price and market_price > 0:
            descuento = round((market_price - float(precio)) / market_price * 100, 2)

        result = await session.execute(select(OportunidadDB).where(OportunidadDB.url == url))
        existing = result.scalar_one_or_none()

        if existing:
            existing.precio_publicado = float(precio)
            existing.precio_mercado_estimado = float(market_price) if market_price else existing.precio_mercado_estimado
            existing.descuento_porcentaje = descuento
            existing.score = score
            self.logger.debug("Updated oportunidad id=%d url=%s", existing.id, url)
            return

        # Every listing is stored, even low-scoring ones: together they are the
        # market sample used by _get_market_price. The UI filters by score.
        session.add(
            OportunidadDB(
                url=url,
                plataforma=listing.get("plataforma") or "desconocida",
                marca=marca,
                modelo=listing.get("modelo") or "Desconocido",
                año=int(año),
                kilometraje=int(kilometraje) if kilometraje else None,
                ubicacion=listing.get("ubicacion"),
                precio_publicado=float(precio),
                precio_mercado_estimado=float(market_price) if market_price else None,
                descuento_porcentaje=descuento,
                score=score,
                descripcion_corta=(listing.get("descripcion") or listing.get("titulo") or "")[:500] or None,
                estado="nueva",
                detectada_en=datetime.now(tz=timezone.utc),
            )
        )
        self.logger.debug(
            "Inserted oportunidad: %s %s %s score=%.1f",
            marca, listing.get("modelo"), año, score,
        )

    # ------------------------------------------------------------------
    # Summary helper
    # ------------------------------------------------------------------

    def summary(self, oportunidades: list[Oportunidad]) -> dict[str, Any]:
        """Return a summary dict suitable for CLI output or logging."""
        if not oportunidades:
            return {"total": 0, "top_5": [], "platforms": {}}

        platform_counts: dict[str, int] = {}
        for op in oportunidades:
            p = op.listing.get("plataforma", "unknown")
            platform_counts[p] = platform_counts.get(p, 0) + 1

        top_5 = [
            {
                "marca": op.listing.get("marca"),
                "modelo": op.listing.get("modelo"),
                "año": op.listing.get("año"),
                "precio": op.listing.get("precio"),
                "score": op.score,
                "descuento_pct": round(op.discount_pct, 1) if op.discount_pct else None,
                "url": op.listing.get("url"),
                "plataforma": op.listing.get("plataforma"),
            }
            for op in oportunidades[:5]
        ]

        scores = [op.score for op in oportunidades]
        return {
            "total": len(oportunidades),
            "avg_score": round(sum(scores) / len(scores), 2),
            "max_score": max(scores),
            "min_score": min(scores),
            "platforms": platform_counts,
            "top_5": top_5,
        }
