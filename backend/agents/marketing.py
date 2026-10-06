"""
Agente de Marketing — writes the sales copy for a vehicle in inventory:
marketplace title (TuCarro / Carroya), catalogue description, Instagram post
and WhatsApp message. Claude writes it when available; otherwise a template
built from the vehicle's real data.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from backend.models import Vehiculo
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
