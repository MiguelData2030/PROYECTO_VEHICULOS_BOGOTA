"""
Demo data generator: one simulated year of a used-car dealership in Bogotá.

Deterministic (fixed seed) so the dataset is the same every time it is loaded.
Prices follow the Colombian 2026 market logic used in the business plan:
  market value = new price × brand retention × age depreciation × mileage factor
  purchase     = 10-20 % below market (the business model)
  sale         = list price minus 0-5 % negotiation
Every record is tagged so it can be removed without touching real data:
  vehiculos.url_fuente == DEMO_TAG, clientes.email ends with DEMO_EMAIL_DOMAIN.
Photos are freely-licensed *reference* pictures of each model (Wikimedia
Commons, see fotos.json) and are credited in the description.
"""

from __future__ import annotations

import json
import random
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

DEMO_TAG = "demo"
DEMO_EMAIL_DOMAIN = "demo.autonegocio.co"

_FOTOS = json.loads((Path(__file__).parent / "fotos.json").read_text(encoding="utf-8"))

# key, marca, modelo, tipo, precio nuevo 2026 (COP), cc, transmisiones, combustible, peso (popularidad)
CATALOGO = [
    ("chevrolet_onix", "Chevrolet", "Onix", "Sedan", 82e6, 1000, ["automatica", "mecanica"], "gasolina", 9),
    ("chevrolet_tracker", "Chevrolet", "Tracker", "SUV", 110e6, 1200, ["automatica"], "gasolina", 8),
    ("chevrolet_captiva", "Chevrolet", "Captiva", "SUV", 115e6, 1500, ["automatica"], "gasolina", 3),
    ("chevrolet_spark_gt", "Chevrolet", "Spark GT", "Hatchback", 52e6, 1200, ["mecanica"], "gasolina", 5),
    ("renault_kwid", "Renault", "Kwid", "Hatchback", 58e6, 1000, ["mecanica"], "gasolina", 4),
    ("renault_sandero", "Renault", "Sandero", "Hatchback", 72e6, 1600, ["mecanica", "automatica"], "gasolina", 6),
    ("renault_logan", "Renault", "Logan", "Sedan", 70e6, 1600, ["mecanica"], "gasolina", 5),
    ("renault_stepway", "Renault", "Stepway", "Hatchback", 80e6, 1600, ["mecanica", "cvt"], "gasolina", 5),
    ("renault_duster", "Renault", "Duster", "SUV", 98e6, 1300, ["mecanica", "automatica"], "gasolina", 8),
    ("renault_koleos", "Renault", "Koleos", "SUV", 165e6, 2500, ["cvt"], "gasolina", 2),
    ("mazda_2", "Mazda", "2 Sedán", "Sedan", 88e6, 1500, ["automatica", "mecanica"], "gasolina", 6),
    ("mazda_3", "Mazda", "3 Touring", "Sedan", 125e6, 2000, ["automatica"], "gasolina", 6),
    ("mazda_cx30", "Mazda", "CX-30", "SUV", 140e6, 2000, ["automatica"], "gasolina", 6),
    ("mazda_cx5", "Mazda", "CX-5", "SUV", 165e6, 2000, ["automatica"], "gasolina", 7),
    ("mazda_cx50", "Mazda", "CX-50", "SUV", 190e6, 2500, ["automatica"], "gasolina", 2),
    ("kia_picanto", "Kia", "Picanto", "Hatchback", 62e6, 1250, ["mecanica", "automatica"], "gasolina", 6),
    ("kia_rio", "Kia", "Rio", "Sedan", 78e6, 1400, ["automatica", "mecanica"], "gasolina", 4),
    ("kia_seltos", "Kia", "Seltos", "SUV", 115e6, 1600, ["automatica"], "gasolina", 4),
    ("kia_sportage", "Kia", "Sportage", "SUV", 160e6, 2000, ["automatica"], "gasolina", 5),
    ("toyota_corolla", "Toyota", "Corolla", "Sedan", 125e6, 1800, ["cvt"], "hibrido", 4),
    ("toyota_corolla_cross", "Toyota", "Corolla Cross", "SUV", 150e6, 1800, ["cvt"], "hibrido", 6),
    ("toyota_rav4", "Toyota", "RAV4", "SUV", 195e6, 2500, ["cvt"], "hibrido", 3),
    ("toyota_hilux", "Toyota", "Hilux", "Pick-up", 210e6, 2400, ["mecanica", "automatica"], "diesel", 5),
    ("toyota_fortuner", "Toyota", "Fortuner", "SUV", 260e6, 2700, ["automatica"], "gasolina", 3),
    ("toyota_prado", "Toyota", "Land Cruiser Prado", "SUV", 420e6, 2800, ["automatica"], "diesel", 2),
    ("hyundai_accent", "Hyundai", "Accent", "Sedan", 80e6, 1600, ["automatica", "mecanica"], "gasolina", 3),
    ("hyundai_creta", "Hyundai", "Creta", "SUV", 110e6, 1600, ["automatica"], "gasolina", 4),
    ("hyundai_tucson", "Hyundai", "Tucson", "SUV", 170e6, 2000, ["automatica"], "gasolina", 4),
    ("nissan_kicks", "Nissan", "Kicks", "SUV", 105e6, 1600, ["cvt"], "gasolina", 5),
    ("nissan_xtrail", "Nissan", "X-Trail", "SUV", 170e6, 2500, ["cvt"], "gasolina", 2),
    ("nissan_frontier", "Nissan", "Frontier", "Pick-up", 190e6, 2300, ["automatica", "mecanica"], "diesel", 3),
    ("vw_tcross", "Volkswagen", "T-Cross", "SUV", 115e6, 1000, ["automatica"], "gasolina", 3),
    ("vw_nivus", "Volkswagen", "Nivus", "SUV", 110e6, 1000, ["automatica"], "gasolina", 2),
    ("vw_amarok", "Volkswagen", "Amarok", "Pick-up", 260e6, 3000, ["automatica"], "diesel", 1),
    ("suzuki_swift", "Suzuki", "Swift", "Hatchback", 70e6, 1200, ["mecanica", "automatica"], "gasolina", 4),
    ("suzuki_vitara", "Suzuki", "Vitara", "SUV", 105e6, 1600, ["automatica"], "gasolina", 3),
    ("ford_escape", "Ford", "Escape", "SUV", 170e6, 2000, ["automatica"], "gasolina", 2),
    ("ford_ranger", "Ford", "Ranger", "Pick-up", 200e6, 2000, ["automatica"], "diesel", 3),
    ("ford_explorer", "Ford", "Explorer", "SUV", 280e6, 2300, ["automatica"], "gasolina", 1),
    ("jeep_compass", "Jeep", "Compass", "SUV", 165e6, 1300, ["automatica"], "gasolina", 2),
    ("mitsubishi_outlander", "Mitsubishi", "Outlander", "SUV", 170e6, 2400, ["cvt"], "gasolina", 2),
    ("bmw_x1", "BMW", "X1 sDrive20i", "SUV", 230e6, 2000, ["automatica"], "gasolina", 2),
    ("mercedes_gla", "Mercedes-Benz", "GLA 200", "SUV", 240e6, 1300, ["automatica"], "gasolina", 2),
    ("audi_q3", "Audi", "Q3", "SUV", 235e6, 1400, ["automatica"], "gasolina", 2),
]

# First model year sold in Colombia (generation shown in the photos)
DESDE = {
    "chevrolet_onix": 2020, "chevrolet_tracker": 2021, "chevrolet_captiva": 2020, "renault_kwid": 2019,
    "renault_stepway": 2020, "renault_sandero": 2020, "renault_logan": 2020, "renault_duster": 2018,
    "renault_koleos": 2017, "mazda_2": 2016, "mazda_3": 2019, "mazda_cx30": 2020, "mazda_cx5": 2017,
    "mazda_cx50": 2023, "kia_picanto": 2018, "kia_rio": 2018, "kia_seltos": 2020, "kia_sportage": 2023,
    "toyota_corolla": 2020, "toyota_corolla_cross": 2021, "toyota_rav4": 2019, "toyota_hilux": 2016,
    "toyota_fortuner": 2016, "toyota_prado": 2018, "hyundai_accent": 2018, "hyundai_creta": 2017,
    "hyundai_tucson": 2022, "nissan_kicks": 2017, "nissan_xtrail": 2018, "nissan_frontier": 2016,
    "vw_tcross": 2020, "vw_nivus": 2021, "vw_amarok": 2017, "suzuki_swift": 2018, "suzuki_vitara": 2016,
    "ford_escape": 2020, "ford_ranger": 2017, "ford_explorer": 2020, "jeep_compass": 2018,
    "mitsubishi_outlander": 2016, "bmw_x1": 2016, "mercedes_gla": 2020, "audi_q3": 2019,
}

# Value retention relative to the market average (business plan, section 2.4)
RETENCION_MARCA = {
    "Toyota": 1.10, "Mazda": 1.05, "Kia": 1.00, "Hyundai": 0.99, "Suzuki": 0.98,
    "Chevrolet": 0.96, "Nissan": 0.96, "Volkswagen": 0.95, "Mitsubishi": 0.94,
    "Ford": 0.93, "Renault": 0.92, "Jeep": 0.91, "BMW": 0.88, "Mercedes-Benz": 0.88, "Audi": 0.87,
}
TRANSMISION_TXT = {"automatica": "automática", "mecanica": "mecánica", "cvt": "automática CVT"}
COLORES = ["Blanco", "Gris", "Negro", "Plata", "Rojo", "Azul", "Blanco perla", "Gris oscuro", "Café"]
PESO_COLOR = [24, 22, 14, 14, 8, 7, 5, 4, 2]
BARRIOS = ["Usaquén", "Chapinero", "Suba", "Kennedy", "Engativá", "Fontibón", "Teusaquillo", "Cedritos",
           "Chía", "Cajicá", "Modelia", "Salitre", "Colina Campestre", "Bosa", "Soacha"]
NOMBRES = ["Juan", "Carlos", "Andrés", "Felipe", "Santiago", "Camilo", "Diego", "Sebastián", "Julián", "Óscar",
           "Laura", "Natalia", "Carolina", "Daniela", "Paula", "Valentina", "Andrea", "Mónica", "Diana", "Catalina",
           "Jorge", "Luis", "Ricardo", "Mauricio", "Alejandra", "Sandra", "Marcela", "Esteban", "David", "Manuela"]
APELLIDOS = ["Rodríguez", "Gómez", "González", "Martínez", "García", "López", "Hernández", "Sánchez", "Ramírez",
             "Pérez", "Torres", "Rojas", "Díaz", "Moreno", "Vargas", "Castro", "Ortiz", "Jiménez", "Muñoz", "Romero",
             "Suárez", "Mejía", "Cárdenas", "Restrepo", "Ospina", "Quintero", "Beltrán", "Parra", "Salazar", "Montoya"]

# Sales per month (seasonality: December bonus season and June "prima"),
# from the first month of operation to the current one.
VENTAS_POR_MES = [3, 4, 5, 7, 5, 4, 5, 6, 8, 7, 8, 9, 2]


@dataclass
class DemoCliente:
    ref: str
    nombre: str
    email: str
    tipo: str
    notas: str
    vehiculos_interes: list = field(default_factory=list)
    presupuesto_min: Optional[float] = None
    presupuesto_max: Optional[float] = None
    creado: Optional[date] = None


@dataclass
class DemoVehiculo:
    ref: str
    datos: dict
    vendedor_ref: str               # who sold it to us
    fecha_compra: date
    precio_compra: float
    gastos_compra: float            # traspaso a nuestro nombre
    reacondicionamiento: float
    venta: Optional[dict] = None    # {"cliente_ref", "fecha", "precio", "comision", "gastos_traspaso", "notas"}


def _slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return "".join(ch for ch in text.lower() if ch.isalnum() or ch == ".")


def _round(value: float, step: int = 100_000) -> float:
    return float(round(value / step) * step)


class _Builder:
    def __init__(self, today: date):
        self.rng = random.Random(2026)
        self.today = today
        self.start = today - timedelta(days=365)
        self.clientes: list[DemoCliente] = []
        self.vehiculos: list[DemoVehiculo] = []
        self._n_cli = 0

    # ---------------------------------------------------------------- people
    def cliente(self, tipo: str, notas: str, creado: date, **extra) -> DemoCliente:
        self._n_cli += 1
        nombre = f"{self.rng.choice(NOMBRES)} {self.rng.choice(APELLIDOS)} {self.rng.choice(APELLIDOS)}"
        first, last = nombre.split()[0], nombre.split()[1]
        c = DemoCliente(
            ref=f"c{self._n_cli}",
            nombre=nombre,
            email=f"{_slug(first)}.{_slug(last)}{self._n_cli}@{DEMO_EMAIL_DOMAIN}",
            tipo=tipo,
            notas=f"[DEMO] {notas}",
            creado=creado,
            **extra,
        )
        self.clientes.append(c)
        return c

    # -------------------------------------------------------------- vehicles
    def _modelo(self, premium_ok: bool = True):
        opciones = [m for m in CATALOGO if premium_ok or m[4] < 230e6]
        return self.rng.choices(opciones, weights=[m[8] for m in opciones])[0]

    def _valor_mercado(self, marca: str, nuevo: float, año: int, km: int) -> float:
        edad = max(0, self.today.year - año)
        # ~18 % the first year, then ~7 % per year (Colombian used prices hold up
        # well: import tariffs keep new cars expensive), adjusted by brand
        factor = 0.84 * (0.935 ** max(0, edad - 1)) if edad else 0.92
        factor *= RETENCION_MARCA.get(marca, 0.95)
        km_esperado = max(1, edad) * 13_000
        factor *= 1 - max(-0.06, min(0.15, (km - km_esperado) / km_esperado * 0.12))
        return nuevo * factor

    def vehiculo(self, fecha_compra: date, escenario: str = "normal", modelo=None) -> DemoVehiculo:
        rng = self.rng
        key, marca, modelo_nombre, tipo, nuevo, cc, transmisiones, combustible, _ = modelo or self._modelo()
        años = list(range(DESDE.get(key, 2016), 2025))
        pesos = {2016: 3, 2017: 5, 2018: 7, 2019: 9, 2020: 10, 2021: 11, 2022: 12, 2023: 10, 2024: 6}
        año = rng.choices(años, weights=[pesos[a] for a in años])[0]
        edad = max(1, self.today.year - año)
        km = int(edad * rng.uniform(8_500, 18_500) / 500) * 500
        mercado = self._valor_mercado(marca, nuevo, año, km)

        descuento_compra = rng.uniform(0.10, 0.20)
        fuente = rng.choices(["particular", "retoma", "subasta", "flota"], weights=[55, 25, 12, 8])[0]
        if fuente == "subasta":
            descuento_compra += 0.06       # cheaper, but more reconditioning
        if escenario == "mala_compra":
            descuento_compra = 0.07        # paid too much + hidden problem
        precio_compra = _round(mercado * (1 - descuento_compra))
        reacond = _round(precio_compra * rng.uniform(0.008, 0.025) + (2_500_000 if fuente == "subasta" else 0), 50_000)
        if escenario == "mala_compra":
            reacond += 7_800_000           # caja automática reparada
        precio_lista = _round(mercado * rng.uniform(0.99, 1.04), 500_000) - 100_000  # "…900.000" pricing
        color = rng.choices(COLORES, weights=PESO_COLOR)[0]
        transmision = rng.choice(transmisiones)
        dueños = rng.choices([1, 2, 3], weights=[55, 35, 10])[0]
        fotos = _FOTOS.get(key) or []

        detalles = [
            f"{marca} {modelo_nombre} {año} con {km:,} km".replace(",", ".")
            + f", transmisión {TRANSMISION_TXT[transmision]}, color {color.lower()}.",
            "Único dueño." if dueños == 1 else f"{dueños} dueños, historial verificado en RUNT.",
            rng.choice([
                "Mantenimientos al día en concesionario.", "Llantas nuevas y revisión de frenos completa.",
                "Peritaje aprobado sin choques estructurales.", "Kit de arrastre y sensores de parqueo.",
                "Cámara de reversa y pantalla táctil con Android Auto / Apple CarPlay.",
            ]),
        ]
        if escenario == "estancado":
            detalles.append("¡Precio rebajado! Recibimos tu carro en parte de pago.")
        if fotos:
            f0 = fotos[0]
            detalles.append(f"Fotos referenciales del modelo: {f0['autor']} ({f0['licencia']}), Wikimedia Commons.")

        vendedor = self.cliente(
            "vendedor" if fuente != "retoma" else "ambos",
            {
                "particular": "Nos vendió su vehículo (particular).",
                "retoma": "Entregó su carro como parte de pago (retoma).",
                "subasta": "Compra en subasta de entidad financiera.",
                "flota": "Renovación de flota corporativa.",
            }[fuente],
            creado=fecha_compra - timedelta(days=rng.randint(1, 10)),
        )

        v = DemoVehiculo(
            ref=f"v{len(self.vehiculos) + 1}",
            vendedor_ref=vendedor.ref,
            fecha_compra=fecha_compra,
            precio_compra=precio_compra,
            gastos_compra=_round(650_000 + precio_compra * 0.004, 10_000),
            reacondicionamiento=reacond,
            datos={
                "marca": marca, "modelo": modelo_nombre, "año": año, "tipo_vehiculo": tipo,
                "color": color, "kilometraje": km, "transmision": transmision, "combustible": combustible,
                "cilindraje": cc, "num_dueños": dueños, "ciudad": "Bogotá",
                "precio_compra": precio_compra, "precio_venta": precio_lista, "precio_mercado": _round(mercado),
                "estado": "disponible", "estado_mecanico": rng.choices(["excelente", "bueno", "regular"], [35, 55, 10])[0],
                "soat_vigente": True, "tecnicomecanica_vigente": edad < 2 or rng.random() > 0.08,
                "impuestos_al_dia": True, "libre_prendas": True,
                "descripcion": " ".join(detalles),
                "fotos": [f["url"] for f in fotos],
                "fuente": fuente, "url_fuente": DEMO_TAG,
                "margen_estimado": round((precio_lista - precio_compra) / precio_compra * 100, 1),
                "score_oportunidad": round(min(95, 45 + descuento_compra * 150 + (8 if marca in ("Toyota", "Mazda") else 0)), 1),
            },
        )
        self.vehiculos.append(v)
        return v

    def vender(self, v: DemoVehiculo, fecha: date, escenario: str = "normal") -> None:
        rng = self.rng
        lista = v.datos["precio_venta"]
        negociacion = rng.uniform(0.0, 0.05)
        if escenario == "estancado":
            negociacion = rng.uniform(0.06, 0.09)
        precio = _round(lista * (1 - negociacion), 500_000)
        forma = rng.choices(["financiado", "contado", "retoma"], weights=[48, 37, 15])[0]
        notas = {
            "financiado": f"Venta financiada: cuota inicial {rng.choice([30, 35, 40, 50])}%, crédito vehicular a {rng.choice([48, 60, 72])} meses.",
            "contado": "Pago de contado por transferencia.",
            "retoma": "El cliente entregó su vehículo como parte de pago.",
        }[forma]
        if escenario == "mala_compra":
            notas += " Pérdida: reparación de caja automática no detectada en el peritaje inicial."
        if escenario == "estancado":
            notas += f" Unidad con {(fecha - v.fecha_compra).days} días en inventario: se rebajó el precio para rotarla."
        comprador = self.cliente(
            "comprador",
            rng.choice(["Llegó por TuCarro.", "Llegó por Instagram.", "Referido de un cliente.",
                        "Visitó la vitrina.", "Escribió por WhatsApp desde la web."]),
            creado=fecha - timedelta(days=rng.randint(2, 20)),
            vehiculos_interes=[{"marca": v.datos["marca"], "modelo": v.datos["modelo"]}],
            presupuesto_max=_round(precio * rng.uniform(1.0, 1.1), 1_000_000),
        )
        v.venta = {
            "cliente_ref": comprador.ref,
            "fecha": fecha,
            "precio": precio,
            "comision": _round(precio * 0.01, 50_000) if rng.random() < 0.25 else 0.0,
            "gastos_traspaso": 0.0,  # el traspaso de venta lo paga el comprador en Bogotá
            "notas": "[DEMO] " + notas,
        }
        v.datos["estado"] = "vendido"

    # ------------------------------------------------------------- the year
    def build(self) -> "_Builder":
        rng = self.rng
        primer_mes = date(self.start.year, self.start.month, 1)
        escenarios_pendientes = ["mala_compra", "estancado", "estancado"]

        for i, objetivo in enumerate(VENTAS_POR_MES):
            y, m = primer_mes.year + (primer_mes.month - 1 + i) // 12, (primer_mes.month - 1 + i) % 12 + 1
            mes_inicio = date(y, m, 1)
            fin_mes = min(self.today, date(y + (m // 12), m % 12 + 1, 1) - timedelta(days=1))
            if mes_inicio > self.today:
                break
            for _ in range(objetivo):
                fecha_venta = mes_inicio + timedelta(days=rng.randint(0, max(0, (fin_mes - mes_inicio).days)))
                escenario = "normal"
                if i in (4, 7) and escenarios_pendientes:
                    escenario = escenarios_pendientes.pop(0)
                dias = {"normal": int(rng.triangular(6, 70, 22)), "mala_compra": 41,
                        "estancado": rng.randint(85, 110)}[escenario]
                fecha_compra = max(self.start - timedelta(days=60), fecha_venta - timedelta(days=dias))
                v = self.vehiculo(fecha_compra, escenario)
                # Toyota / Mazda rotate faster
                if v.datos["marca"] in ("Toyota", "Mazda") and escenario == "normal":
                    v.fecha_compra = fecha_venta - timedelta(days=max(4, dias // 2))
                self.vender(v, fecha_venta, escenario)

        # Current stock: what is on the lot today
        for estado, dias_rango, n in [("disponible", (2, 45), 13), ("reservado", (10, 30), 3),
                                      ("en_proceso", (0, 6), 3), ("disponible", (68, 95), 2)]:
            for _ in range(n):
                v = self.vehiculo(self.today - timedelta(days=rng.randint(*dias_rango)),
                                  "estancado" if dias_rango[0] > 60 else "normal")
                v.datos["estado"] = estado
                if estado == "reservado":
                    v.datos["descripcion"] += " (Separado con abono, entrega pendiente de crédito.)"
                if estado == "en_proceso":
                    v.datos["descripcion"] += " (En alistamiento: taller y fotos profesionales.)"

        # Open leads from the website: people who want to sell or buy
        for _ in range(16):
            vende = rng.random() < 0.55
            marca_modelo = self._modelo(premium_ok=False)
            año = rng.randint(2015, 2023)
            creado = self.today - timedelta(days=rng.randint(0, 25))
            if vende:
                valor = self._valor_mercado(marca_modelo[1], marca_modelo[4], año, (self.today.year - año) * 13_000)
                self.cliente("vendedor", f"Lead web (formulario Vender): ofrece su {marca_modelo[1]} {marca_modelo[2]} {año}.",
                             creado, vehiculos_interes=[{"marca": marca_modelo[1], "modelo": marca_modelo[2], "anio": año,
                                                        "precio_esperado": f"{_round(valor * 1.05, 1_000_000):,.0f}".replace(",", ".")}])
            else:
                tope = _round(rng.choice([50, 70, 90, 120, 160, 220]) * 1e6)
                self.cliente("comprador", f"Lead web (Contacto): busca {marca_modelo[3]} hasta ${tope:,.0f}.".replace(",", "."),
                             creado, presupuesto_min=_round(tope * 0.7), presupuesto_max=tope,
                             vehiculos_interes=[{"tipo": marca_modelo[3], "marca": marca_modelo[1]}])
        return self


def build_demo(today: Optional[date] = None) -> tuple[list[DemoCliente], list[DemoVehiculo]]:
    b = _Builder(today or date.today()).build()
    return b.clientes, b.vehiculos
