"""
Price analysis engine for AutoNegocio.

Capabilities:
- Compute market average / median prices by brand / model / year
- Detect price anomalies (unusually cheap = buying opportunity)
- Track price trends over time (requires historical data in DB)
- Generate price reports
- analyze_opportunity(listing) → enriched dict with score, market_price,
  discount_pct, and a human-readable recommendation
"""

from __future__ import annotations

import logging
import statistics
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.database import AsyncSessionLocal
from ..models.vehiculo import Vehiculo
from .scraper_manager import ScraperManager, CURRENT_YEAR

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# A listing is "anomalously cheap" if its price is this many standard
# deviations below the group mean.
ANOMALY_THRESHOLD_STD = 1.5

# Minimum number of reference records needed for a reliable average
MIN_SAMPLE_SIZE = 3

# Recommendation thresholds
SCORE_EXCELLENT = 70.0
SCORE_GOOD = 50.0
SCORE_AVERAGE = 30.0


# ---------------------------------------------------------------------------
# PriceAnalyzer
# ---------------------------------------------------------------------------

class PriceAnalyzer:
    """Analyses scraped listing prices against market data stored in the DB."""

    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        """
        Parameters
        ----------
        session : AsyncSession, optional
            If provided, the analyzer uses this session.
            If None, a new session is created per operation.
        """
        self._session = session
        self.logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Context manager helpers
    # ------------------------------------------------------------------

    async def _get_session(self) -> AsyncSession:
        if self._session:
            return self._session
        # Caller must manage the lifecycle when no session is injected
        raise RuntimeError(
            "No session provided.  Either inject one or use "
            "async with PriceAnalyzer.from_db() as analyzer: ..."
        )

    @classmethod
    async def from_db(cls) -> "PriceAnalyzer":
        """Factory that creates a standalone instance with its own session."""
        session = AsyncSessionLocal()
        return cls(session=session)

    async def close(self) -> None:
        if self._session:
            await self._session.close()

    async def __aenter__(self) -> "PriceAnalyzer":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Core: market price statistics
    # ------------------------------------------------------------------

    async def get_market_stats(
        self,
        marca: str,
        modelo: Optional[str] = None,
        año: Optional[int] = None,
        year_window: int = 1,
    ) -> dict[str, Any]:
        """
        Fetch price statistics for a brand/model/year combination.

        Parameters
        ----------
        marca : str
        modelo : str, optional
        año : int, optional
        year_window : int
            How many years either side of `año` to include (default 1).

        Returns
        -------
        dict with keys: count, mean, median, std, min, max, samples
        """
        session = await self._get_session()

        conditions = [
            Vehiculo.marca.ilike(marca),
            Vehiculo.precio_mercado.isnot(None),
        ]
        if modelo:
            conditions.append(Vehiculo.modelo.ilike(modelo))
        if año:
            conditions.append(
                Vehiculo.año.between(int(año) - year_window, int(año) + year_window)
            )

        result = await session.execute(
            select(Vehiculo.precio_mercado).where(and_(*conditions))
        )
        prices = [row[0] for row in result.fetchall() if row[0]]

        if not prices:
            return {
                "count": 0,
                "mean": None,
                "median": None,
                "std": None,
                "min": None,
                "max": None,
                "samples": [],
            }

        return {
            "count": len(prices),
            "mean": statistics.mean(prices),
            "median": statistics.median(prices),
            "std": statistics.stdev(prices) if len(prices) >= 2 else 0.0,
            "min": min(prices),
            "max": max(prices),
            "samples": prices,
        }

    async def calculate_market_averages(self) -> list[dict[str, Any]]:
        """
        Compute and return average prices for every (marca, modelo, año)
        combination present in the DB.

        Returns a list of dicts sorted by marca/modelo/año.
        """
        session = await self._get_session()

        result = await session.execute(
            select(
                Vehiculo.marca,
                Vehiculo.modelo,
                Vehiculo.año,
                func.count(Vehiculo.id).label("count"),
                func.avg(Vehiculo.precio_mercado).label("avg_price"),
                func.min(Vehiculo.precio_mercado).label("min_price"),
                func.max(Vehiculo.precio_mercado).label("max_price"),
            )
            .where(Vehiculo.precio_mercado.isnot(None))
            .group_by(Vehiculo.marca, Vehiculo.modelo, Vehiculo.año)
            .order_by(Vehiculo.marca, Vehiculo.modelo, Vehiculo.año)
        )

        rows = result.fetchall()
        averages = []
        for row in rows:
            averages.append(
                {
                    "marca": row.marca,
                    "modelo": row.modelo,
                    "año": row.año,
                    "count": row.count,
                    "avg_price": round(row.avg_price) if row.avg_price else None,
                    "min_price": row.min_price,
                    "max_price": row.max_price,
                }
            )

        self.logger.info("Calculated market averages for %d groups", len(averages))
        return averages

    # ------------------------------------------------------------------
    # Anomaly detection
    # ------------------------------------------------------------------

    async def detect_anomalies(
        self,
        listings: list[dict],
        *,
        threshold_std: float = ANOMALY_THRESHOLD_STD,
    ) -> list[dict]:
        """
        Given a list of normalized listing dicts, return those whose price is
        anomalously low compared to the market group average.

        A listing is flagged when:
            precio < mean - threshold_std * std

        Parameters
        ----------
        listings : list[dict]  — already normalized
        threshold_std : float  — z-score threshold (default 1.5)

        Returns
        -------
        Subset of listings that are anomalously cheap, each annotated with:
            _anomaly_market_mean, _anomaly_std, _anomaly_z_score
        """
        anomalies: list[dict] = []

        for listing in listings:
            marca = listing.get("marca")
            modelo = listing.get("modelo")
            año = listing.get("año")
            precio = listing.get("precio")

            if not (marca and precio):
                continue

            stats = await self.get_market_stats(marca, modelo, año)
            if stats["count"] < MIN_SAMPLE_SIZE:
                # Not enough data for a reliable comparison
                continue

            mean = stats["mean"]
            std = stats["std"]

            if std == 0:
                continue

            z_score = (mean - precio) / std
            if z_score >= threshold_std:
                annotated = dict(listing)
                annotated["_anomaly_market_mean"] = round(mean)
                annotated["_anomaly_std"] = round(std)
                annotated["_anomaly_z_score"] = round(z_score, 2)
                anomalies.append(annotated)
                self.logger.info(
                    "Anomaly detected: %s %s %s @ %d COP  (mean=%d, z=%.2f)",
                    marca, modelo, año, precio, mean, z_score,
                )

        self.logger.info(
            "Anomaly detection: %d anomalies in %d listings",
            len(anomalies), len(listings),
        )
        return anomalies

    # ------------------------------------------------------------------
    # Price trend tracking
    # ------------------------------------------------------------------

    async def get_price_trend(
        self,
        marca: str,
        modelo: Optional[str] = None,
        *,
        months: int = 6,
    ) -> list[dict[str, Any]]:
        """
        Return a monthly price trend for the given marca/modelo over the past
        `months` months, using the created_at timestamp of Vehiculo records.

        Returns a list of dicts: [{"month": "2026-04", "avg_price": ..., "count": ...}]
        """
        session = await self._get_session()

        since = datetime.now(tz=timezone.utc) - timedelta(days=months * 30)
        conditions = [
            Vehiculo.marca.ilike(marca),
            Vehiculo.precio_mercado.isnot(None),
            Vehiculo.created_at >= since,
        ]
        if modelo:
            conditions.append(Vehiculo.modelo.ilike(modelo))

        result = await session.execute(
            select(
                Vehiculo.created_at,
                Vehiculo.precio_mercado,
            ).where(and_(*conditions)).order_by(Vehiculo.created_at)
        )
        rows = result.fetchall()

        if not rows:
            return []

        # Bucket by month
        monthly: dict[str, list[float]] = {}
        for created_at, price in rows:
            if created_at is None or price is None:
                continue
            month_key = created_at.strftime("%Y-%m")
            monthly.setdefault(month_key, []).append(price)

        trend = [
            {
                "month": month,
                "avg_price": round(statistics.mean(prices)),
                "median_price": round(statistics.median(prices)),
                "count": len(prices),
            }
            for month, prices in sorted(monthly.items())
        ]

        self.logger.debug(
            "Price trend for %s %s: %d monthly data points",
            marca, modelo or "all models", len(trend),
        )
        return trend

    # ------------------------------------------------------------------
    # Main public API: analyze_opportunity
    # ------------------------------------------------------------------

    async def analyze_opportunity(self, listing: dict) -> dict[str, Any]:
        """
        Enrich a normalized listing dict with price analysis output.

        Parameters
        ----------
        listing : dict — normalized listing (output of BaseScraper.normalize)

        Returns
        -------
        dict with keys:
            score           float  0-100
            market_price    int|None  (COP)
            discount_pct    float|None
            recommendation  str   ("Excelente oportunidad" | "Buena oportunidad" |
                                   "Oportunidad moderada" | "Precio de mercado" |
                                   "Precio sobre el mercado")
            details         dict  (breakdown of score components)
            anomaly         bool
            market_stats    dict  (mean, median, std, count)
        """
        marca = listing.get("marca")
        modelo = listing.get("modelo")
        año = listing.get("año")
        precio = listing.get("precio")

        # Fetch market statistics
        stats = await self.get_market_stats(marca or "", modelo, año)
        market_price = int(stats["mean"]) if stats.get("mean") else None

        # Opportunity score (reuse ScraperManager formula)
        score = ScraperManager.calculate_score(listing, market_price)

        # Discount percentage
        discount_pct: Optional[float] = None
        if market_price and precio and market_price > 0:
            discount_pct = round((market_price - precio) / market_price * 100, 1)

        # Anomaly flag
        anomaly = False
        if (
            stats["count"] >= MIN_SAMPLE_SIZE
            and stats.get("std")
            and stats["std"] > 0
            and precio
            and stats.get("mean")
        ):
            z_score = (stats["mean"] - precio) / stats["std"]
            anomaly = z_score >= ANOMALY_THRESHOLD_STD

        # Human-readable recommendation
        recommendation = self._recommendation(score, discount_pct)

        # Score breakdown
        details = self._score_details(listing, market_price)

        result = {
            "score": score,
            "market_price": market_price,
            "discount_pct": discount_pct,
            "recommendation": recommendation,
            "anomaly": anomaly,
            "market_stats": {
                "count": stats["count"],
                "mean": round(stats["mean"]) if stats.get("mean") else None,
                "median": round(stats["median"]) if stats.get("median") else None,
                "std": round(stats["std"]) if stats.get("std") else None,
                "min": stats.get("min"),
                "max": stats.get("max"),
            },
            "details": details,
        }

        self.logger.info(
            "analyze_opportunity: %s %s %s | score=%.1f | market=%s | discount=%s%% | %s",
            marca, modelo, año,
            score,
            f"{market_price:,}" if market_price else "N/A",
            f"{discount_pct:.1f}" if discount_pct is not None else "N/A",
            recommendation,
        )
        return result

    # ------------------------------------------------------------------
    # Price reports
    # ------------------------------------------------------------------

    async def generate_price_report(self) -> dict[str, Any]:
        """
        Generate a summary price report across all scraped data in the DB.

        Returns
        -------
        dict with:
            generated_at    str   ISO timestamp
            total_vehicles  int
            by_brand        list[dict]  — avg price, count, per brand
            top_deals       list[dict]  — highest score_oportunidad vehicles
            anomalies_count int
        """
        session = await self._get_session()

        # Total vehicles
        total_result = await session.execute(
            select(func.count(Vehiculo.id)).where(Vehiculo.precio_mercado.isnot(None))
        )
        total = total_result.scalar() or 0

        # By-brand summary
        brand_result = await session.execute(
            select(
                Vehiculo.marca,
                func.count(Vehiculo.id).label("count"),
                func.avg(Vehiculo.precio_mercado).label("avg_price"),
                func.avg(Vehiculo.score_oportunidad).label("avg_score"),
            )
            .where(Vehiculo.precio_mercado.isnot(None))
            .group_by(Vehiculo.marca)
            .order_by(func.count(Vehiculo.id).desc())
        )
        by_brand = [
            {
                "marca": row.marca,
                "count": row.count,
                "avg_price": round(row.avg_price) if row.avg_price else None,
                "avg_score": round(row.avg_score, 1) if row.avg_score else None,
            }
            for row in brand_result.fetchall()
        ]

        # Top 10 deals by score
        top_result = await session.execute(
            select(Vehiculo)
            .where(Vehiculo.score_oportunidad.isnot(None))
            .order_by(Vehiculo.score_oportunidad.desc())
            .limit(10)
        )
        top_deals = [
            {
                "id": v.id,
                "marca": v.marca,
                "modelo": v.modelo,
                "año": v.año,
                "precio_mercado": v.precio_mercado,
                "score": v.score_oportunidad,
                "url": v.url_fuente,
                "fuente": v.fuente,
            }
            for v in top_result.scalars().all()
        ]

        report = {
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "total_vehicles": total,
            "by_brand": by_brand,
            "top_deals": top_deals,
            "anomalies_count": None,  # populate by calling detect_anomalies separately
        }

        self.logger.info(
            "Price report generated: %d vehicles, %d brands",
            total, len(by_brand),
        )
        return report

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _recommendation(score: float, discount_pct: Optional[float]) -> str:
        if score >= SCORE_EXCELLENT:
            return "Excelente oportunidad — compra recomendada"
        elif score >= SCORE_GOOD:
            return "Buena oportunidad — vale la pena investigar"
        elif score >= SCORE_AVERAGE:
            return "Oportunidad moderada — negociar precio"
        elif discount_pct is not None and discount_pct > 0:
            return "Precio ligeramente bajo al mercado"
        elif discount_pct is not None and discount_pct < -5:
            return "Precio sobre el mercado — no recomendado"
        else:
            return "Precio de mercado — sin ventaja clara"

    @staticmethod
    def _score_details(listing: dict, market_price: Optional[int]) -> dict[str, Any]:
        """Return a breakdown of which scoring criteria were met."""
        from .scraper_manager import BRAND_SCORE, TIPO_SCORE, POPULAR_COLORS

        marca = (listing.get("marca") or "").lower()
        tipo = (listing.get("tipo_vehiculo") or "").lower()
        año = listing.get("año") or 0
        precio = listing.get("precio") or 0
        kilometraje = listing.get("kilometraje") or 0
        transmision = (listing.get("transmision") or "").lower()
        color = (listing.get("color") or "").lower()
        ubicacion = (listing.get("ubicacion") or "").lower()

        price_pts = 0.0
        if market_price and precio and precio < market_price:
            price_pts = min(40.0, (market_price - precio) / market_price * 100)

        brand_pts = BRAND_SCORE.get(marca, 0)

        tipo_pts = 0
        for tipo_key, pts in TIPO_SCORE.items():
            if tipo_key in tipo:
                tipo_pts = pts
                break

        age_pts = 0
        if año:
            age = CURRENT_YEAR - int(año)
            age_pts = max(0, 10 - age)

        km_pts = 0
        if año and kilometraje:
            age = max(1, CURRENT_YEAR - int(año))
            kpy = int(kilometraje) / age
            km_pts = 10 if kpy < 12_000 else (5 if kpy < 18_000 else 0)

        trans_pts = 5 if ("automatica" in transmision or "automática" in transmision or "automatico" in transmision) else 0
        color_pts = 5 if any(c in color for c in POPULAR_COLORS) else 0
        loc_pts = 5 if "bogot" in ubicacion else 0

        return {
            "precio_descuento":  round(price_pts, 2),
            "marca_popularidad": brand_pts,
            "tipo_vehiculo":     tipo_pts,
            "edad_vehiculo":     age_pts,
            "kilometraje":       km_pts,
            "transmision":       trans_pts,
            "color":             color_pts,
            "ubicacion":         loc_pts,
        }
