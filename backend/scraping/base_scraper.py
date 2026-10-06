"""
Base scraper — abstract class every platform scraper inherits from.

Provides:
- Async HTTP fetching via httpx with retry + exponential back-off
- User-agent rotation
- Rate limiting (min delay between requests)
- Abstract parse() hook
- normalize() to produce a canonical listing dict
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from abc import ABC, abstractmethod
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# User-agent pool – realistic desktop browsers (Windows / Mac / Linux)
# ---------------------------------------------------------------------------
USER_AGENTS: list[str] = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Chrome macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Firefox macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    # Safari macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]

# Canonical listing fields — every scraper must produce these keys.
LISTING_FIELDS: tuple[str, ...] = (
    "marca",
    "modelo",
    "año",
    "precio",
    "kilometraje",
    "transmision",
    "combustible",
    "color",
    "tipo_vehiculo",
    "ubicacion",
    "url",
    "plataforma",
    "descripcion",
    "fotos",
)


class BaseScraper(ABC):
    """
    Abstract base for all AutoNegocio platform scrapers.

    Sub-classes must implement:
        - parse(html, url) -> list[dict]
        - scrape(**filters) -> list[dict]   (high-level entry point)
    """

    # Seconds to wait between consecutive requests to the same domain
    REQUEST_DELAY: float = 1.5
    # Maximum jitter added on top of REQUEST_DELAY (seconds)
    JITTER: float = 1.0
    # HTTP timeout (connect + read)
    TIMEOUT: float = 20.0
    # Maximum retry attempts
    MAX_RETRIES: int = 3
    # Initial back-off delay (doubles each retry)
    BACKOFF_BASE: float = 2.0

    def __init__(self) -> None:
        self._last_request_ts: dict[str, float] = {}  # domain -> timestamp
        self._client: Optional[httpx.AsyncClient] = None
        self.logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # HTTP client lifecycle
    # ------------------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        """Return a shared async httpx client (lazily created)."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.TIMEOUT),
                follow_redirects=True,
                headers=self._base_headers(),
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Headers helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _random_user_agent() -> str:
        return random.choice(USER_AGENTS)

    def _base_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self._random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",  # no "br": brotli isn't installed → undecodable bytes
            "Connection": "keep-alive",
            "DNT": "1",
        }

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    async def _rate_limit(self, url: str) -> None:
        """Sleep if needed to respect per-domain request delay."""
        domain = urlparse(url).netloc
        now = time.monotonic()
        last = self._last_request_ts.get(domain, 0.0)
        elapsed = now - last
        desired_gap = self.REQUEST_DELAY + random.uniform(0, self.JITTER)
        if elapsed < desired_gap:
            sleep_time = desired_gap - elapsed
            self.logger.debug("Rate limit: sleeping %.2fs for %s", sleep_time, domain)
            await asyncio.sleep(sleep_time)
        self._last_request_ts[domain] = time.monotonic()

    # ------------------------------------------------------------------
    # Fetch with retry + back-off
    # ------------------------------------------------------------------

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        retries: int = MAX_RETRIES,
    ) -> str:
        """
        Fetch a URL and return the response body as text.

        Retries up to `retries` times with exponential back-off on transient
        errors (network issues, 429, 5xx).  Raises httpx.HTTPStatusError on
        permanent client errors (4xx except 429).
        """
        await self._rate_limit(url)

        client = await self._get_client()

        # Rotate UA on every request
        merged_headers = {"User-Agent": self._random_user_agent()}
        if headers:
            merged_headers.update(headers)

        last_exc: Exception | None = None

        for attempt in range(1, retries + 1):
            try:
                self.logger.debug("Fetching [%d/%d] %s", attempt, retries, url)
                response = await client.request(
                    method,
                    url,
                    params=params,
                    headers=merged_headers,
                )

                # Raise for permanent client errors
                if response.status_code in (400, 401, 403, 404):
                    self.logger.warning(
                        "HTTP %d for %s — not retrying", response.status_code, url
                    )
                    response.raise_for_status()

                # Treat 429 / 5xx as transient
                if response.status_code == 429 or response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"Transient HTTP {response.status_code}",
                        request=response.request,
                        response=response,
                    )

                response.raise_for_status()
                self.logger.debug("OK %d — %s", response.status_code, url)
                return response.text

            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                last_exc = exc
                if attempt == retries:
                    break
                backoff = self.BACKOFF_BASE ** attempt + random.uniform(0, 1)
                self.logger.warning(
                    "Attempt %d failed for %s: %s — retrying in %.1fs",
                    attempt, url, exc, backoff,
                )
                await asyncio.sleep(backoff)

        self.logger.error("All %d attempts failed for %s: %s", retries, url, last_exc)
        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def parse(self, html: str, url: str) -> list[dict]:
        """
        Parse raw HTML from a search-results or detail page.

        Returns a list of raw dicts; each will be passed through normalize().
        """
        ...

    @abstractmethod
    async def scrape(self, **filters: Any) -> list[dict]:
        """
        High-level entry point: build URLs, paginate, parse, and return
        a list of normalized listing dicts.
        """
        ...

    # ------------------------------------------------------------------
    # Normalisation
    # ------------------------------------------------------------------

    def normalize(self, raw: dict) -> dict:
        """
        Convert a raw parsed dict into the canonical listing format.

        Missing fields default to None; numeric fields are coerced.
        String fields are stripped and lower-cased where appropriate.
        """
        def _int(val: Any) -> Optional[int]:
            if val is None:
                return None
            try:
                # Strip common formatting: "120.000 km", "$45.000.000"
                cleaned = str(val).replace(".", "").replace(",", "").replace("$", "").strip()
                # Remove trailing non-numeric suffix (e.g. " km", " cc")
                numeric_part = ""
                for ch in cleaned:
                    if ch.isdigit():
                        numeric_part += ch
                    elif numeric_part:
                        break
                return int(numeric_part) if numeric_part else None
            except (ValueError, TypeError):
                return None

        def _float(val: Any) -> Optional[float]:
            if val is None:
                return None
            try:
                cleaned = str(val).replace(".", "").replace(",", ".").replace("$", "").strip()
                return float(cleaned)
            except (ValueError, TypeError):
                return None

        def _str(val: Any) -> Optional[str]:
            if val is None:
                return None
            return str(val).strip() or None

        def _lower(val: Any) -> Optional[str]:
            s = _str(val)
            return s.lower() if s else None

        fotos = raw.get("fotos")
        if isinstance(fotos, str):
            fotos = [fotos] if fotos else []
        elif fotos is None:
            fotos = []

        return {
            "marca":        _str(raw.get("marca")),
            "modelo":       _str(raw.get("modelo")),
            "año":          _int(raw.get("año") or raw.get("anio") or raw.get("year")),
            "precio":       _int(raw.get("precio") or raw.get("price")),
            "kilometraje":  _int(raw.get("kilometraje") or raw.get("km") or raw.get("mileage")),
            "transmision":  _lower(raw.get("transmision") or raw.get("transmission")),
            "combustible":  _lower(raw.get("combustible") or raw.get("fuel")),
            "color":        _lower(raw.get("color")),
            "tipo_vehiculo": _str(raw.get("tipo_vehiculo") or raw.get("tipo") or raw.get("body_type")),
            "ubicacion":    _str(raw.get("ubicacion") or raw.get("location") or raw.get("ciudad")),
            "url":          _str(raw.get("url")),
            "plataforma":   _str(raw.get("plataforma") or raw.get("platform")),
            "descripcion":  _str(raw.get("descripcion") or raw.get("description")),
            "fotos":        fotos,
        }
