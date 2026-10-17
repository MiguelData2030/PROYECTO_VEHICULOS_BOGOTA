"""
Agente de Logística — arma las rutas del día para peritajes a domicilio,
entregas de carros vendidos y test drives.

Reglas:
  1. Reparte las citas entre los conductores por zona (sector alrededor de la
     sede), equilibrando el tiempo de trabajo de cada uno.
  2. Ordena cada ruta respetando la ventana horaria del cliente: elige siempre
     la siguiente cita factible que deja menos tiempo muerto (viaje + espera),
     dando prioridad a la que vence primero.
  3. Mejora la ruta intercambiando tramos (2-opt) mientras no se incumpla
     ninguna ventana.

Línea base para comparar: el despachador asigna las citas en el orden en que
llegaron, alternando conductores, sin mirar el mapa.
"""

from __future__ import annotations

import math

VELOCIDAD_KMH = 20      # promedio en Bogotá con tráfico de sábado
FACTOR_CALLES = 1.35    # distancia en calles vs línea recta
INICIO = 8 * 60         # 08:00
CONDUCTORES = 2
COSTO_KM = 1_100        # combustible + desgaste, COP por km
COSTO_HORA = 18_000     # costo de la hora del conductor, COP


def _min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _hhmm(minutos: float) -> str:
    m = int(round(minutos))
    return f"{m // 60:02d}:{m % 60:02d}"


def km(a: dict, b: dict) -> float:
    r = 6371.0
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dp, dl = p2 - p1, math.radians(b["lon"] - a["lon"])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h)) * FACTOR_CALLES


def _viaje(a: dict, b: dict) -> float:
    return km(a, b) / VELOCIDAD_KMH * 60


def simular_ruta(sede: dict, ruta: list[dict]) -> dict:
    """Recorre la ruta en orden: horas de llegada, esperas, retrasos y km."""
    t, pos, total_km, espera, paradas, tarde = INICIO, sede, 0.0, 0.0, [], 0
    for c in ruta:
        d = km(pos, c)
        total_km += d
        t += _viaje(pos, c)
        if t < _min(c["desde"]):
            espera += _min(c["desde"]) - t
            t = _min(c["desde"])
        retraso = max(0.0, t - _min(c["hasta"]))
        tarde += retraso > 0
        paradas.append({"cita": c["id"], "tipo": c["tipo"], "zona": c["zona"], "llegada": _hhmm(t),
                        "ventana": f"{c['desde']}-{c['hasta']}", "retraso_min": round(retraso)})
        t += c["duracion_min"]
        pos = c
    total_km += km(pos, sede)
    t += _viaje(pos, sede)
    return {"paradas": paradas, "km": round(total_km, 1), "fin": _hhmm(t),
            "horas": round((t - INICIO) / 60, 2), "espera_min": round(espera), "citas_tarde": tarde}


def _factible(sede: dict, ruta: list[dict]) -> bool:
    return simular_ruta(sede, ruta)["citas_tarde"] == 0


def _ordenar(sede: dict, citas: list[dict]) -> list[dict]:
    pendientes, ruta, t, pos = list(citas), [], INICIO, sede
    while pendientes:
        def costo(c):
            llegada = t + _viaje(pos, c)
            inicio = max(llegada, _min(c["desde"]))
            tardanza = max(0, inicio - _min(c["hasta"]))
            return (tardanza > 0, inicio - t + 0.15 * (_min(c["hasta"]) - inicio), tardanza)
        c = min(pendientes, key=costo)
        pendientes.remove(c)
        t = max(t + _viaje(pos, c), _min(c["desde"])) + c["duracion_min"]
        ruta.append(c)
        pos = c
    # 2-opt: invierte tramos si la ruta queda más corta y sigue cumpliendo
    mejor = simular_ruta(sede, ruta)
    mejoro = True
    while mejoro:
        mejoro = False
        for i in range(len(ruta) - 1):
            for j in range(i + 2, len(ruta) + 1):
                prueba = ruta[:i] + ruta[i:j][::-1] + ruta[j:]
                r = simular_ruta(sede, prueba)
                if r["citas_tarde"] <= mejor["citas_tarde"] and r["km"] < mejor["km"] - 0.05:
                    ruta, mejor, mejoro = prueba, r, True
    return ruta


def _repartir(sede: dict, citas: list[dict]) -> list[list[dict]]:
    """Sectores alrededor de la sede, cortados para equilibrar el trabajo."""
    ang = sorted(citas, key=lambda c: math.atan2(c["lat"] - sede["lat"], c["lon"] - sede["lon"]))
    carga_total = sum(c["duracion_min"] + 2 * _viaje(sede, c) for c in ang)
    grupos, actual, carga = [], [], 0.0
    for c in ang:
        actual.append(c)
        carga += c["duracion_min"] + 2 * _viaje(sede, c)
        if len(grupos) < CONDUCTORES - 1 and carga >= carga_total / CONDUCTORES:
            grupos.append(actual)
            actual, carga = [], 0.0
    grupos.append(actual)
    return grupos


def _resumen(rutas: list[dict]) -> dict:
    km_total = sum(r["km"] for r in rutas)
    horas = sum(r["horas"] for r in rutas)
    return {
        "km": round(km_total, 1),
        "horas_conductor": round(horas, 1),
        "citas_tarde": sum(r["citas_tarde"] for r in rutas),
        "costo_cop": round(km_total * COSTO_KM + horas * COSTO_HORA, -3),
    }


def analizar(sede: dict, citas: list[dict]) -> dict:
    # Línea base: orden de llegada, conductores alternados
    base = [simular_ruta(sede, citas[i::CONDUCTORES]) for i in range(CONDUCTORES)]
    # Agente
    grupos = _repartir(sede, citas)
    rutas = [simular_ruta(sede, _ordenar(sede, g)) for g in grupos]
    rb, ra = _resumen(base), _resumen(rutas)
    ahorro_km = rb["km"] - ra["km"]
    ahorro_h = rb["horas_conductor"] - ra["horas_conductor"]
    return {
        "citas": len(citas),
        "conductores": CONDUCTORES,
        "linea_base": rb,
        "agente": ra,
        "ahorro": {
            "km": round(ahorro_km, 1),
            "km_pct": round(ahorro_km / rb["km"] * 100, 1),
            "horas": round(ahorro_h, 1),
            "costo_cop": rb["costo_cop"] - ra["costo_cop"],
            "costo_mes_cop": (rb["costo_cop"] - ra["costo_cop"]) * 22,  # 22 días de operación
            "citas_tarde_evitadas": rb["citas_tarde"] - ra["citas_tarde"],
        },
        "rutas": [{"conductor": i + 1, **r} for i, r in enumerate(rutas)],
        "recomendacion": (
            f"Con {CONDUCTORES} conductores las {len(citas)} citas se cubren en {ra['km']} km y "
            f"{ra['horas_conductor']} horas, con {ra['citas_tarde']} llegadas tarde "
            f"(antes: {rb['km']} km, {rb['horas_conductor']} horas y {rb['citas_tarde']} llegadas tarde)."
        ),
        "supuestos": f"Velocidad {VELOCIDAD_KMH} km/h; calles = línea recta × {str(FACTOR_CALLES).replace('.', ',')}; "
                     f"${COSTO_KM:,} por km y ${COSTO_HORA:,} por hora de conductor; 22 días al mes."
                     .replace(",", ".").replace("× 1.35", "× 1,35"),
    }
