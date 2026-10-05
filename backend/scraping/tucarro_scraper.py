"""
TuCarro.com.co scraper — MercadoLibre's Colombian car platform.

Target base URL:
    https://carros.tucarro.com.co/usados/bogota/

Listing cards use MercadoLibre Andes UI Kit class names:
    .ui-search-result__wrapper
    .andes-money-amount
    .ui-search-item__title
    etc.

Detail pages use a similar layout with attribute rows.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup, Tag

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

PLATFORM = "tucarro"
BASE_URL = "https://carros.tucarro.com.co"
SEARCH_URL = f"{BASE_URL}/usados/bogota/"

# Mapping from TuCarro attribute label text to our canonical key
ATTRIBUTE_MAP: dict[str, str] = {
    "kilometraje":   "kilometraje",
    "kilómetros":    "kilometraje",
    "km":            "kilometraje",
    "año":           "año",
    "transmisión":   "transmision",
    "transmision":   "transmision",
    "combustible":   "combustible",
    "color":         "color",
    "tipo de vehículo": "tipo_vehiculo",
    "tipo vehículo": "tipo_vehiculo",
    "tipo":          "tipo_vehiculo",
    "carrocería":    "tipo_vehiculo",
    "ciudad":        "ubicacion",
    "ubicación":     "ubicacion",
    "ubicacion":     "ubicacion",
}


class TuCarroScraper(BaseScraper):
    """Scrapes used car listings from TuCarro.com.co (Bogotá)."""

    # Seconds between requests (be polite to ML servers)
    REQUEST_DELAY: float = 2.0
    JITTER: float = 1.5
    # Max pages to paginate through per search
    MAX_PAGES: int = 10
    # Results per page (TuCarro default)
    PAGE_SIZE: int = 48

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
        Construct a TuCarro search URL.

        TuCarro / MercadoLibre encode pagination as an offset in the path:
            _Desde_49   → page 2  (0-based offset of first result)
        Filters are appended as query parameters or path fragments.
        """
        # Start with the base search path
        path = SEARCH_URL

        # Brand filter is encoded as a path segment like /toyota/
        if marca:
            path = f"{BASE_URL}/usados/bogota/{marca.lower()}/"

        # Build query params for price and year ranges
        params: dict[str, str] = {}
        if precio_min is not None:
            params["PRICE_MIN"] = str(precio_min)
        if precio_max is not None:
            params["PRICE_MAX"] = str(precio_max)
        if año_min is not None:
            params["YEAR_MIN"] = str(año_min)
        if año_max is not None:
            params["YEAR_MAX"] = str(año_max)

        # Pagination: offset = (page - 1) * PAGE_SIZE + 1
        if page > 1:
            offset = (page - 1) * self.PAGE_SIZE + 1
            path = path.rstrip("/") + f"_Desde_{offset}_NoIndex_True"

        if params:
            return f"{path}?{urlencode(params)}"
        return path

    # ------------------------------------------------------------------
    # High-level scrape entry point
    # ------------------------------------------------------------------

    async def scrape(self, **filters: Any) -> list[dict]:
        """
        Scrape TuCarro for used cars in Bogotá.

        Accepted keyword filters:
            marca       (str)   e.g. "toyota"
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
            "Starting TuCarro scrape | filters=%s | max_pages=%d",
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

            # If we got fewer results than a full page, we've hit the last page
            if len(raw_listings) < self.PAGE_SIZE:
                self.logger.info("Partial page (%d < %d) — reached last page", len(raw_listings), self.PAGE_SIZE)
                break

        self.logger.info("TuCarro scrape complete: %d total listings", len(all_listings))
        return all_listings

    # ------------------------------------------------------------------
    # HTML parsing — search results page
    # ------------------------------------------------------------------

    async def parse(self, html: str, url: str) -> list[dict]:
        """Parse a TuCarro search results page and return raw listing dicts."""
        soup = BeautifulSoup(html, "html.parser")
        listings: list[dict] = []

        # MercadoLibre / TuCarro wraps each card in one of these containers
        cards = (
            soup.select("li.ui-search-layout__item")
            or soup.select("li[class*='ui-search-layout__item']")
            or soup.select(".ui-search-result__wrapper")
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
        """Extract data from a single search result card."""
        raw: dict[str, Any] = {"plataforma": PLATFORM}

        # --- URL ---
        link = card.select_one("a.ui-search-item__group__element, a.ui-search-result__image__element, a[href*='tucarro.com.co']")
        if not link:
            link = card.find("a", href=True)
        if link:
            href = link.get("href", "")
            raw["url"] = href if href.startswith("http") else urljoin(BASE_URL, href)

        # --- Title → marca + modelo ---
        title_tag = (
            card.select_one("h2.ui-search-item__title")
            or card.select_one(".ui-search-item__title")
            or card.select_one("h2")
        )
        if title_tag:
            title = title_tag.get_text(strip=True)
            raw["titulo"] = title
            marca, modelo = self._split_title(title)
            raw["marca"] = marca
            raw["modelo"] = modelo

        # --- Price ---
        price_tag = (
            card.select_one(".andes-money-amount__fraction")
            or card.select_one("[class*='andes-money-amount__fraction']")
        )
        if price_tag:
            raw["precio"] = price_tag.get_text(strip=True)

        # --- Thumbnail ---
        img = card.select_one("img.ui-search-result-image__element, img[data-src], img[src]")
        if img:
            src = img.get("data-src") or img.get("src") or ""
            if src and not src.startswith("data:"):
                raw["fotos"] = [src]

        # --- Attributes on card (year, km, etc.) ---
        attr_rows = (
            card.select("ul.ui-search-card-attributes__list li")
            or card.select(".ui-search-item__group--attributes li")
            or card.select("[class*='ui-search-card-attributes'] li")
        )
        for attr in attr_rows:
            text = attr.get_text(strip=True).lower()
            self._extract_inline_attribute(text, raw)

        # --- Location ---
        location_tag = (
            card.select_one(".ui-search-item__location-label")
            or card.select_one("[class*='ui-search-item__location']")
            or card.select_one(".ui-search-item__group--location")
        )
        if location_tag:
            raw["ubicacion"] = location_tag.get_text(strip=True)
        else:
            raw["ubicacion"] = "Bogotá"

        return raw if raw.get("url") else None

    def _extract_inline_attribute(self, text: str, raw: dict) -> None:
        """Try to extract year/km from inline card attribute text."""
        # Year: 4-digit number between 1990-2030
        year_match = re.search(r"\b(19[9]\d|20[0-2]\d)\b", text)
        if year_match and "año" not in raw:
            raw["año"] = year_match.group(1)
            return
        # Kilometraje
        km_match = re.search(r"([\d.,]+)\s*km", text)
        if km_match and "kilometraje" not in raw:
            raw["kilometraje"] = km_match.group(1)

    # ------------------------------------------------------------------
    # HTML parsing — detail page
    # ------------------------------------------------------------------

    async def parse_detail(self, url: str) -> dict:
        """
        Fetch and parse a TuCarro listing detail page.

        Returns a dict with all available attributes, ready for normalize().
        """
        self.logger.debug("Parsing detail page: %s", url)
        try:
            html = await self.fetch(url)
        except Exception as exc:
            self.logger.error("Failed to fetch detail %s: %s", url, exc)
            return {}

        soup = BeautifulSoup(html, "html.parser")
        raw: dict[str, Any] = {"url": url, "plataforma": PLATFORM}

        # --- Title ---
        title_tag = (
            soup.select_one("h1.ui-pdp-title")
            or soup.select_one("h1[class*='ui-pdp']")
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
            soup.select_one(".ui-pdp-price .andes-money-amount__fraction")
            or soup.select_one(".price-tag-fraction")
            or soup.select_one("[class*='price'] [class*='fraction']")
        )
        if price_tag:
            raw["precio"] = price_tag.get_text(strip=True)

        # --- Attributes table ---
        attr_rows = (
            soup.select(".ui-vip-striped-specs__table .andes-table__row")
            or soup.select(".ui-pdp-specs .ui-pdp-specs__table tr")
            or soup.select("[class*='vip-specs'] tr, [class*='ui-pdp-specs'] tr")
            or soup.select("table tr")
        )
        for row in attr_rows:
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).lower()
                value = cells[1].get_text(strip=True)
                self._map_attribute(label, value, raw)

        # Also try spec lists (dl/dt/dd pattern)
        for dt in soup.select(".ui-pdp-specs__spec"):
            label_tag = dt.select_one(".ui-pdp-specs__label, dt")
            value_tag = dt.select_one(".ui-pdp-specs__value, dd")
            if label_tag and value_tag:
                label = label_tag.get_text(strip=True).lower()
                value = value_tag.get_text(strip=True)
                self._map_attribute(label, value, raw)

        # --- Description ---
        desc_tag = (
            soup.select_one(".ui-pdp-description__content")
            or soup.select_one("[class*='description'] p")
            or soup.select_one(".ui-pdp-description")
        )
        if desc_tag:
            raw["descripcion"] = desc_tag.get_text(separator=" ", strip=True)

        # --- Photos ---
        photos: list[str] = []
        for img in soup.select(".ui-pdp-gallery img, .ui-pdp-image img"):
            src = img.get("data-zoom") or img.get("data-src") or img.get("src") or ""
            if src and not src.startswith("data:") and src not in photos:
                photos.append(src)
        if photos:
            raw["fotos"] = photos

        # --- Location ---
        loc_tag = (
            soup.select_one(".ui-vip-seller-data__subtitle")
            or soup.select_one("[class*='seller-data'] [class*='subtitle']")
            or soup.select_one(".ui-pdp-seller-info__subtitle")
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
        """
        Attempt to split a listing title like "Toyota Corolla 2020" into
        (marca, modelo).  Falls back to (title, "") if splitting is ambiguous.
        """
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
                # Remove trailing year
                modelo = re.sub(r"\s+\d{4}\s*$", "", modelo).strip()
                return brand, modelo
        # Fallback: first word is brand
        parts = title_stripped.split(None, 1)
        return (parts[0], parts[1].strip() if len(parts) > 1 else "")

    def _map_attribute(self, label: str, value: str, raw: dict) -> None:
        """Map a label/value pair into raw using ATTRIBUTE_MAP."""
        for key_fragment, field in ATTRIBUTE_MAP.items():
            if key_fragment in label:
                raw[field] = value
                return
        # Fallback heuristics
        if re.match(r"^(19[9]\d|20[0-2]\d)$", value.strip()):
            raw.setdefault("año", value.strip())
        elif re.search(r"\d+\s*km", value.lower()):
            raw.setdefault("kilometraje", value)

    # ------------------------------------------------------------------
    # Async context manager support
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "TuCarroScraper":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
