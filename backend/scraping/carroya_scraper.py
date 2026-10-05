"""
Carroya.com scraper — one of Colombia's leading independent car marketplaces.

Target base URL:
    https://www.carroya.com/vehiculos/usados/bogota

Carroya uses a React-rendered page but also exposes structured HTML for
search engine crawlers.  Card class names follow Carroya's own design system.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup, Tag

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

PLATFORM = "carroya"
BASE_URL = "https://www.carroya.com"
SEARCH_URL = f"{BASE_URL}/vehiculos/usados/bogota"

# Label → canonical field mapping for Carroya detail pages
ATTRIBUTE_MAP: dict[str, str] = {
    "año":             "año",
    "año del modelo":  "año",
    "modelo":          "año",       # Carroya sometimes calls year "Modelo"
    "kilometraje":     "kilometraje",
    "kilómetros":      "kilometraje",
    "km":              "kilometraje",
    "transmisión":     "transmision",
    "transmision":     "transmision",
    "tipo de transmisión": "transmision",
    "combustible":     "combustible",
    "tipo de combustible": "combustible",
    "color":           "color",
    "color exterior":  "color",
    "tipo de vehículo": "tipo_vehiculo",
    "tipo de carrocería": "tipo_vehiculo",
    "carrocería":      "tipo_vehiculo",
    "ciudad":          "ubicacion",
    "ubicación":       "ubicacion",
    "cilindraje":      "cilindraje",
}

# Carroya year-range query param name
_YEAR_MIN_PARAM = "minAnio"
_YEAR_MAX_PARAM = "maxAnio"
_PRICE_MIN_PARAM = "minPrecio"
_PRICE_MAX_PARAM = "maxPrecio"
_BRAND_PARAM = "marca"
_PAGE_PARAM = "pagina"


class CarroyaScraper(BaseScraper):
    """Scrapes used car listings from Carroya.com (Bogotá)."""

    REQUEST_DELAY: float = 2.0
    JITTER: float = 1.5
    MAX_PAGES: int = 10
    # Carroya typically shows 24 results per page
    PAGE_SIZE: int = 24

    # ------------------------------------------------------------------
    # URL builders
    # ------------------------------------------------------------------

    def build_search_url(
        self,
        *,
        marca: Optional[str] = None,
        precio_min: Optional[int] = None,
        precio_max: Optional[int] = None,
        año_min: Optional[int] = None,
        año_max: Optional[int] = None,
        page: int = 1,
    ) -> str:
        """
        Build a Carroya search URL.

        Carroya uses query parameters for all filters and pagination:
            https://www.carroya.com/vehiculos/usados/bogota?pagina=2&marca=Toyota
        """
        params: dict[str, Any] = {}

        if marca:
            params[_BRAND_PARAM] = marca

        if precio_min is not None:
            params[_PRICE_MIN_PARAM] = precio_min
        if precio_max is not None:
            params[_PRICE_MAX_PARAM] = precio_max
        if año_min is not None:
            params[_YEAR_MIN_PARAM] = año_min
        if año_max is not None:
            params[_YEAR_MAX_PARAM] = año_max

        if page > 1:
            params[_PAGE_PARAM] = page

        if params:
            return f"{SEARCH_URL}?{urlencode(params)}"
        return SEARCH_URL

    # ------------------------------------------------------------------
    # High-level scrape entry point
    # ------------------------------------------------------------------

    async def scrape(self, **filters: Any) -> list[dict]:
        """
        Scrape Carroya for used cars in Bogotá.

        Accepted keyword filters:
            marca       (str)   e.g. "Toyota"
            precio_min  (int)   COP
            precio_max  (int)   COP
            año_min     (int)   e.g. 2015
            año_max     (int)   e.g. 2024
            max_pages   (int)   override MAX_PAGES
        """
        max_pages = int(filters.pop("max_pages", self.MAX_PAGES))
        all_listings: list[dict] = []
        seen_urls: set[str] = set()

        self.logger.info(
            "Starting Carroya scrape | filters=%s | max_pages=%d",
            filters, max_pages,
        )

        for page in range(1, max_pages + 1):
            url = self.build_search_url(page=page, **filters)
            self.logger.info("Scraping page %d → %s", page, url)

            try:
                html = await self.fetch(url)
            except Exception as exc:
                self.logger.error("Failed to fetch page %d: %s", page, exc)
                break

            raw_listings = await self.parse(html, url)

            if not raw_listings:
                self.logger.info("No listings on page %d — stopping pagination", page)
                break

            new = 0
            for raw in raw_listings:
                listing = self.normalize(raw)
                listing_url = listing.get("url", "")
                if listing_url and listing_url not in seen_urls:
                    seen_urls.add(listing_url)
                    all_listings.append(listing)
                    new += 1

            self.logger.info("Page %d: %d new listings (total %d)", page, new, len(all_listings))

            if len(raw_listings) < self.PAGE_SIZE:
                self.logger.info(
                    "Partial page (%d < %d) — reached last page",
                    len(raw_listings), self.PAGE_SIZE,
                )
                break

        self.logger.info("Carroya scrape complete: %d total listings", len(all_listings))
        return all_listings

    # ------------------------------------------------------------------
    # HTML parsing — search results page
    # ------------------------------------------------------------------

    async def parse(self, html: str, url: str) -> list[dict]:
        """Parse a Carroya search results page."""
        soup = BeautifulSoup(html, "html.parser")
        listings: list[dict] = []

        # Carroya listing cards — try several possible selectors
        cards = (
            soup.select("article.vehicle-card")
            or soup.select("[class*='vehicle-card']")
            or soup.select("[class*='VehicleCard']")
            or soup.select(".listing-item")
            or soup.select("[data-testid='vehicle-card']")
            or soup.select(".car-card")
            # Generic fallback: any article with a link inside
            or [
                tag for tag in soup.find_all("article")
                if tag.find("a", href=True)
            ]
        )

        if not cards:
            self.logger.debug("No listing cards found at %s", url)
            return []

        for card in cards:
            try:
                raw = self._parse_card(card)
                if raw:
                    listings.append(raw)
            except Exception as exc:
                self.logger.debug("Error parsing card: %s", exc)
                continue

        return listings

    def _parse_card(self, card: Tag) -> Optional[dict]:
        """Extract data from a single Carroya listing card."""
        raw: dict[str, Any] = {"plataforma": PLATFORM}

        # --- URL ---
        link = (
            card.select_one("a[href*='/detalle/'], a[href*='/vehiculo/']")
            or card.select_one("a.vehicle-card__link, a[class*='card-link']")
            or card.find("a", href=True)
        )
        if link:
            href = link.get("href", "")
            raw["url"] = href if href.startswith("http") else urljoin(BASE_URL, href)

        # --- Title → marca + modelo ---
        title_tag = (
            card.select_one("h2.vehicle-card__title, h2[class*='title'], h3[class*='title']")
            or card.select_one("[class*='vehicle-name'], [class*='car-name']")
            or card.select_one("h2, h3")
        )
        if title_tag:
            title = title_tag.get_text(strip=True)
            raw["titulo"] = title
            marca, modelo = self._split_title(title)
            raw["marca"] = marca
            raw["modelo"] = modelo

        # --- Price ---
        price_tag = (
            card.select_one("[class*='price__value'], [class*='precio']")
            or card.select_one(".vehicle-card__price, [class*='card-price']")
            or card.select_one("[class*='price']")
        )
        if price_tag:
            raw["precio"] = price_tag.get_text(strip=True)

        # --- Year ---
        year_tag = (
            card.select_one("[class*='year'], [class*='anio'], [class*='año']")
            or card.select_one("[data-label='Año'], [data-label='año']")
        )
        if year_tag:
            year_text = year_tag.get_text(strip=True)
            year_match = re.search(r"\b(19[9]\d|20[0-2]\d)\b", year_text)
            if year_match:
                raw["año"] = year_match.group(1)

        # --- Kilometraje ---
        km_tag = (
            card.select_one("[class*='mileage'], [class*='km'], [class*='kilometraje']")
            or card.select_one("[data-label='Kilometraje'], [data-label='km']")
        )
        if km_tag:
            raw["kilometraje"] = km_tag.get_text(strip=True)

        # --- Inline text attributes (fallback) ---
        # Some cards list attributes as plain text items
        detail_items = (
            card.select(".vehicle-card__details li, [class*='card-details'] li")
            or card.select(".vehicle-specs li, [class*='specs'] li")
            or card.select("ul li")
        )
        for item in detail_items:
            text = item.get_text(strip=True).lower()
            self._extract_inline_attribute(text, raw)

        # --- Location ---
        loc_tag = (
            card.select_one("[class*='location'], [class*='ciudad'], [class*='ubicacion']")
            or card.select_one("[data-label='Ciudad']")
        )
        if loc_tag:
            raw["ubicacion"] = loc_tag.get_text(strip=True)
        else:
            raw["ubicacion"] = "Bogotá"

        # --- Thumbnail ---
        img = (
            card.select_one("img.vehicle-card__image, img[class*='card-image']")
            or card.select_one("img[data-src], img[src]")
        )
        if img:
            src = img.get("data-src") or img.get("src") or ""
            if src and not src.startswith("data:"):
                raw["fotos"] = [src]

        return raw if raw.get("url") else None

    def _extract_inline_attribute(self, text: str, raw: dict) -> None:
        """Try to extract year/km from inline card attribute text."""
        year_match = re.search(r"\b(19[9]\d|20[0-2]\d)\b", text)
        if year_match and "año" not in raw:
            raw["año"] = year_match.group(1)
            return
        km_match = re.search(r"([\d.,]+)\s*km", text)
        if km_match and "kilometraje" not in raw:
            raw["kilometraje"] = km_match.group(1)

    # ------------------------------------------------------------------
    # HTML parsing — detail page
    # ------------------------------------------------------------------

    async def parse_detail(self, url: str) -> dict:
        """
        Fetch and parse a Carroya listing detail page.

        Returns a dict ready to be passed through normalize().
        """
        self.logger.debug("Parsing Carroya detail page: %s", url)
        try:
            html = await self.fetch(url)
        except Exception as exc:
            self.logger.error("Failed to fetch detail %s: %s", url, exc)
            return {}

        soup = BeautifulSoup(html, "html.parser")
        raw: dict[str, Any] = {"url": url, "plataforma": PLATFORM}

        # --- Title ---
        title_tag = (
            soup.select_one("h1.vehicle-detail__title, h1[class*='title']")
            or soup.select_one("h1")
        )
        if title_tag:
            title = title_tag.get_text(strip=True)
            raw["titulo"] = title
            marca, modelo = self._split_title(title)
            raw["marca"] = marca
            raw["modelo"] = modelo

        # --- Price ---
        price_tag = (
            soup.select_one(".vehicle-detail__price [class*='value']")
            or soup.select_one("[class*='detail-price'], [class*='precio-detalle']")
            or soup.select_one("[class*='price']")
        )
        if price_tag:
            raw["precio"] = price_tag.get_text(strip=True)

        # --- Attributes (table or dl/dt/dd) ---
        # Carroya detail pages use a spec table
        spec_rows = (
            soup.select(".vehicle-specs__table tr, [class*='specs-table'] tr")
            or soup.select(".vehicle-detail__specs tr")
            or soup.select("table tr")
        )
        for row in spec_rows:
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).lower()
                value = cells[1].get_text(strip=True)
                self._map_attribute(label, value, raw)

        # Also try dl lists
        for dl in soup.select(".vehicle-specs__list dl, [class*='specs-list'] dl"):
            dt = dl.find("dt")
            dd = dl.find("dd")
            if dt and dd:
                label = dt.get_text(strip=True).lower()
                value = dd.get_text(strip=True)
                self._map_attribute(label, value, raw)

        # Also try key-value pairs in divs (common React pattern)
        for spec_item in soup.select(
            "[class*='spec-item'], [class*='attribute-item'], [class*='detail-item']"
        ):
            label_tag = spec_item.select_one("[class*='label'], [class*='key'], dt, th")
            value_tag = spec_item.select_one("[class*='value'], [class*='val'], dd, td")
            if label_tag and value_tag:
                label = label_tag.get_text(strip=True).lower()
                value = value_tag.get_text(strip=True)
                self._map_attribute(label, value, raw)

        # --- Description ---
        desc_tag = (
            soup.select_one(".vehicle-detail__description, [class*='description-text']")
            or soup.select_one("[class*='descripcion']")
        )
        if desc_tag:
            raw["descripcion"] = desc_tag.get_text(separator=" ", strip=True)

        # --- Photos ---
        photos: list[str] = []
        for img in soup.select(
            ".vehicle-gallery img, [class*='gallery'] img, [class*='photo'] img"
        ):
            src = img.get("data-zoom") or img.get("data-src") or img.get("src") or ""
            if src and not src.startswith("data:") and src not in photos:
                photos.append(src)
        if photos:
            raw["fotos"] = photos

        # --- Location ---
        loc_tag = (
            soup.select_one("[class*='seller-location'], [class*='ciudad-vendedor']")
            or soup.select_one("[class*='location']")
        )
        if loc_tag:
            raw["ubicacion"] = loc_tag.get_text(strip=True)
        elif "ubicacion" not in raw:
            raw["ubicacion"] = "Bogotá"

        return raw

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _split_title(title: str) -> tuple[str, str]:
        """Split 'Toyota Corolla 2020' → ('Toyota', 'Corolla')."""
        known_brands = [
            "Toyota", "Mazda", "Chevrolet", "Kia", "Renault", "Hyundai",
            "Nissan", "Ford", "Volkswagen", "Suzuki", "Honda", "Mitsubishi",
            "Jeep", "BMW", "Mercedes-Benz", "Mercedes", "Audi", "Volvo",
            "Subaru", "Peugeot", "Fiat", "Seat", "Skoda", "Dodge", "Ram",
            "GMC", "BYD", "Chery", "JAC", "Geely", "Great Wall", "DFSK",
        ]
        title_stripped = title.strip()
        for brand in known_brands:
            if title_stripped.lower().startswith(brand.lower()):
                modelo = title_stripped[len(brand):].strip()
                modelo = re.sub(r"\s+\d{4}\s*$", "", modelo).strip()
                return brand, modelo
        parts = title_stripped.split(None, 1)
        return (parts[0], parts[1].strip() if len(parts) > 1 else "")

    def _map_attribute(self, label: str, value: str, raw: dict) -> None:
        """Map a label/value pair into raw using ATTRIBUTE_MAP."""
        for key_fragment, field in ATTRIBUTE_MAP.items():
            if key_fragment in label:
                # Special case: Carroya uses "Modelo" for the year on some pages
                if key_fragment == "modelo" and re.match(r"^(19[9]\d|20[0-2]\d)$", value.strip()):
                    raw.setdefault("año", value.strip())
                else:
                    raw.setdefault(field, value)
                return
        # Heuristic fallbacks
        if re.match(r"^(19[9]\d|20[0-2]\d)$", value.strip()):
            raw.setdefault("año", value.strip())
        elif re.search(r"\d+\s*km", value.lower()):
            raw.setdefault("kilometraje", value)

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "CarroyaScraper":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
