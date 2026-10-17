"""
Datos simulados para los agentes nuevos de AutoNegocio.

Todo se genera con una semilla fija: cada ejecución produce exactamente los
mismos datos, así los resultados de la simulación se pueden repetir y auditar.
Los nombres, direcciones y cifras son ficticios.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

SEMILLA = 2026
DATA_DIR = Path(__file__).parent / "data"

# Sede de AutoNegocio (Calle 80 con Avenida 68, Bogotá)
SEDE = {"nombre": "Sede AutoNegocio (Calle 80)", "lat": 4.6880, "lon": -74.0780}

# Centro aproximado de cada zona atendida
ZONAS = {
    "Usaquén": (4.7020, -74.0320),
    "Cedritos": (4.7240, -74.0400),
    "Chapinero": (4.6450, -74.0620),
    "Suba": (4.7410, -74.0840),
    "Engativá": (4.7070, -74.1120),
    "Fontibón": (4.6710, -74.1410),
    "Salitre": (4.6510, -74.1060),
    "Teusaquillo": (4.6390, -74.0830),
    "Kennedy": (4.6280, -74.1520),
    "Puente Aranda": (4.6160, -74.1110),
    "Bosa": (4.6180, -74.1920),
    "Chía": (4.8610, -74.0580),
}

NOMBRES = ["Andrés", "Camila", "Juan", "Valentina", "Santiago", "Laura", "Felipe", "Daniela",
           "Carlos", "Natalia", "Sebastián", "Paula", "Diego", "Mariana", "Julián", "Carolina",
           "Mateo", "Juliana", "Alejandro", "Sara", "David", "Manuela", "Óscar", "Lina"]
APELLIDOS = ["Gómez", "Rodríguez", "Martínez", "López", "García", "Pérez", "Sánchez", "Ramírez",
             "Torres", "Díaz", "Vargas", "Rojas", "Moreno", "Castro", "Ortiz", "Suárez"]

# Inventario disponible (marca, modelo, año, km, tipo, precio COP, liquidez)
INVENTARIO = [
    ("Chevrolet", "Spark GT", 2021, 67000, "Hatchback", 32_900_000, "alta"),
    ("Kia", "Picanto", 2022, 52000, "Hatchback", 41_900_000, "alta"),
    ("Renault", "Sandero", 2022, 68000, "Hatchback", 44_900_000, "alta"),
    ("Kia", "Rio", 2020, 106500, "Sedan", 45_900_000, "media"),
    ("Mazda", "2 Sedán", 2022, 73000, "Sedan", 62_400_000, "alta"),
    ("Renault", "Duster", 2020, 82000, "SUV", 55_900_000, "alta"),
    ("Chevrolet", "Tracker", 2021, 79500, "SUV", 66_900_000, "alta"),
    ("Hyundai", "Creta", 2022, 41000, "SUV", 82_900_000, "media"),
    ("Mazda", "3 Touring", 2023, 12000, "Sedan", 95_000_000, "alta"),
    ("Kia", "Sportage", 2021, 58000, "SUV", 98_500_000, "media"),
    ("Toyota", "Corolla Cross", 2022, 38000, "SUV", 119_900_000, "alta"),
    ("Mazda", "CX-30", 2023, 21000, "SUV", 121_500_000, "alta"),
    ("Toyota", "Corolla Híbrido", 2024, 3800, "Sedan", 135_000_000, "alta"),
    ("Mazda", "CX-5", 2022, 35000, "SUV", 139_900_000, "alta"),
    ("Toyota", "Fortuner", 2020, 55500, "SUV", 175_900_000, "media"),
    ("Ford", "Ranger", 2021, 61000, "Pick-up", 149_900_000, "media"),
    ("Nissan", "Kicks", 2021, 47000, "SUV", 72_900_000, "media"),
    ("Volkswagen", "T-Cross", 2022, 29000, "SUV", 92_900_000, "media"),
    ("Suzuki", "Swift", 2022, 33000, "Hatchback", 54_900_000, "media"),
    ("Renault", "Logan", 2019, 91000, "Sedan", 34_900_000, "alta"),
]


def _nombre(rng: random.Random) -> str:
    return f"{rng.choice(NOMBRES)} {rng.choice(APELLIDOS)}"


def inventario() -> list[dict]:
    claves = ("marca", "modelo", "año", "kilometraje", "tipo", "precio", "liquidez")
    return [{"id": i + 1, **dict(zip(claves, fila))} for i, fila in enumerate(INVENTARIO)]


# ---------------------------------------------------------------- logística
def citas_del_dia(rng: random.Random) -> list[dict]:
    """
    Agenda de un sábado: peritajes a domicilio (carros que el negocio va a
    comprar), entregas de carros vendidos y test drives a domicilio.
    El orden de la lista es el orden en que llegaron las solicitudes.
    """
    tipos = [("peritaje", 45), ("entrega", 60), ("test_drive", 40)]
    ventanas = [("mañana", "08:00", "12:00"), ("tarde", "13:00", "17:30"), ("flexible", "08:00", "17:30")]
    citas = []
    zonas = list(ZONAS)
    for i in range(18):
        tipo, minutos = rng.choices(tipos, weights=[5, 3, 2])[0]
        zona = rng.choice(zonas)
        lat, lon = ZONAS[zona]
        nombre_v, desde, hasta = rng.choices(ventanas, weights=[4, 4, 3])[0]
        citas.append({
            "id": f"C{i + 1:02d}",
            "tipo": tipo,
            "cliente": _nombre(rng),
            "zona": zona,
            "lat": round(lat + rng.uniform(-0.009, 0.009), 5),
            "lon": round(lon + rng.uniform(-0.009, 0.009), 5),
            "ventana": nombre_v,
            "desde": desde,
            "hasta": hasta,
            "duracion_min": minutos,
        })
    return citas


# ------------------------------------------------------------- alistamiento
TAREAS = [
    # tarea, días base, costo base (COP), probabilidad de que el carro la necesite
    ("mecanica", 2, 850_000, 0.75),
    ("latoneria_pintura", 3, 1_400_000, 0.45),
    ("llantas_alineacion", 1, 1_100_000, 0.40),
    ("lavado_detallado", 1, 280_000, 1.00),
    ("fotos_publicacion", 1, 0, 1.00),
]


def compras_por_alistar(rng: random.Random) -> list[dict]:
    """Carros recién comprados que esperan alistamiento antes de publicarse."""
    out = []
    for i in range(14):
        marca, modelo, año, km, tipo, precio, liquidez = rng.choice(INVENTARIO)
        compra = round(precio * rng.uniform(0.78, 0.86), -5)
        tareas = []
        for nombre, dias, costo, prob in TAREAS:
            if rng.random() < prob:
                tareas.append({
                    "tarea": nombre,
                    "dias": dias + (1 if rng.random() < 0.25 and dias > 1 else 0),
                    "costo": round(costo * rng.uniform(0.8, 1.4), -4),
                })
        out.append({
            "id": f"A{i + 1:02d}",
            "vehiculo": f"{marca} {modelo} {año}",
            "kilometraje": km,
            "liquidez": liquidez,
            "precio_compra": compra,
            "precio_venta": precio,
            # misma fórmula de costos del Agente Valuador (sin traspaso): 650.000 + 1,9 % del precio
            "presupuesto_alistamiento": round(650_000 + precio * 0.019, -4),
            "dia_compra": i // 3,  # llegan 3 carros por día hábil
            "tareas": tareas,
        })
    return out


# -------------------------------------------------------------------- crédito
EMPLEOS = ["empleado", "independiente", "pensionado"]


def solicitudes_credito(rng: random.Random) -> list[dict]:
    """Compradores que piden financiación para un carro del inventario."""
    inv = inventario()
    out = []
    for i in range(25):
        carro = rng.choice(inv)
        ingreso = round(rng.choice([2.8, 3.5, 4.2, 5.0, 6.5, 8.0, 10.0, 14.0]) * 1_000_000 * rng.uniform(0.9, 1.15), -4)
        out.append({
            "id": f"S{i + 1:02d}",
            "cliente": _nombre(rng),
            "empleo": rng.choices(EMPLEOS, weights=[6, 3, 1])[0],
            "ingreso_mensual": ingreso,
            "cuotas_actuales": round(ingreso * rng.choice([0, 0, 0.05, 0.10, 0.18, 0.25]), -4),
            "puntaje_buro": rng.randint(480, 880),
            "vehiculo_id": carro["id"],
            "vehiculo": f"{carro['marca']} {carro['modelo']} {carro['año']}",
            "precio": carro["precio"],
            "cuota_inicial": round(carro["precio"] * rng.choice([0.10, 0.20, 0.30, 0.40]), -5),
        })
    return out


# ------------------------------------------------------------------ atención
PLANTILLAS = [
    # (intención esperada, texto con marcadores)
    ("comprar", "Hola, busco una {tipo} {marca} de hasta {ppto} millones, ¿qué tienen?"),
    ("comprar", "Buenas, necesito un carro automático para la familia, presupuesto {ppto} millones"),
    ("comprar", "Quiero comprar un {marca} usado, ¿tienen disponibles?"),
    ("comprar", "Hola! Estoy buscando {tipo} modelo 2021 en adelante, tengo {ppto} millones de contado, lo necesito esta semana"),
    ("vender", "Hola, quiero vender mi {marca} 2019, ¿cuánto me dan?"),
    ("vender", "Buenas tardes, ustedes compran carros? Tengo un {marca} con 80.000 km"),
    ("vender", "Necesito vender mi carro rápido, me pagan de contado?"),
    ("financiacion", "¿Financian? Gano {ingreso} millones al mes y quiero un carro"),
    ("financiacion", "Cuánto quedaría la cuota mensual del {marca} si doy el 30% de inicial?"),
    ("financiacion", "Hola, reportado en datacrédito puedo sacar carro con ustedes?"),
    ("disponibilidad", "¿El {marca} que publicaron en Instagram todavía está disponible? ¿Precio?"),
    ("disponibilidad", "Hola, vi el {marca} en TuCarro, ¿sigue disponible?"),
    ("cita", "¿Dónde quedan? Quiero ir a ver carros el sábado"),
    ("cita", "Puedo ir mañana a hacer test drive? a qué hora abren"),
    ("queja", "Compré un carro con ustedes y el aire acondicionado no funciona, necesito que me respondan"),
    ("queja", "Llevo 3 días esperando los papeles del traspaso, muy mal servicio"),
]
CANALES = ["whatsapp", "instagram", "facebook", "tiktok", "web"]


def mensajes_entrantes(rng: random.Random) -> list[dict]:
    """Mensajes que llegan por WhatsApp y redes en un día."""
    out = []
    for i in range(40):
        intencion, plantilla = rng.choice(PLANTILLAS)
        texto = plantilla.format(
            marca=rng.choice(["Mazda", "Toyota", "Kia", "Chevrolet", "Renault", "Hyundai"]),
            tipo=rng.choice(["camioneta", "SUV", "sedán", "hatchback"]),
            ppto=rng.choice([45, 60, 80, 100, 130]),
            ingreso=rng.choice([3, 4, 6, 9]),
        )
        out.append({
            "id": f"M{i + 1:02d}",
            "canal": rng.choice(CANALES),
            "cliente": _nombre(rng),
            "hora": f"{rng.randint(7, 21):02d}:{rng.randint(0, 59):02d}",
            "texto": texto,
            "intencion_real": intencion,  # etiqueta para medir la precisión del agente
        })
    return sorted(out, key=lambda m: m["hora"])


def generar() -> dict:
    rng = random.Random(SEMILLA)
    datos = {
        "sede": SEDE,
        "inventario": inventario(),
        "citas": citas_del_dia(rng),
        "alistamiento": compras_por_alistar(rng),
        "credito": solicitudes_credito(rng),
        "mensajes": mensajes_entrantes(rng),
    }
    DATA_DIR.mkdir(exist_ok=True)
    for clave, valor in datos.items():
        (DATA_DIR / f"{clave}.json").write_text(json.dumps(valor, ensure_ascii=False, indent=2), encoding="utf-8")
    return datos


if __name__ == "__main__":
    d = generar()
    print({k: len(v) if isinstance(v, list) else 1 for k, v in d.items()})
