"""
Agente de Alistamiento — organiza el taller: en qué orden se alistan los
carros recién comprados para que lleguen al catálogo lo antes posible.

Cada carro pasa por sus tareas en orden (mecánica → latonería y pintura →
llantas → lavado → fotos). Cada área atiende un número limitado de carros a
la vez. Mientras un carro está en el taller su capital está parado y cuesta.

Regla del agente: atender primero el carro que más capital libera por día de
trabajo (costo diario del capital × liquidez ÷ días de taller pendientes).
Es la regla clásica de programación "más peso por menor tiempo" (WSPT).
También avisa cuando el alistamiento supera el presupuesto que usó el
Agente Valuador al comprar el carro (650.000 + 1,9 % del precio).

Línea base: el taller atiende por orden de llegada (FIFO).
"""

from __future__ import annotations

ORDEN = ["mecanica", "latoneria_pintura", "llantas_alineacion", "lavado_detallado", "fotos_publicacion"]
CAPACIDAD = {"mecanica": 2, "latoneria_pintura": 1, "llantas_alineacion": 1, "lavado_detallado": 2, "fotos_publicacion": 2}
NOMBRE = {"mecanica": "mecánica", "latoneria_pintura": "latonería y pintura", "llantas_alineacion": "llantas",
          "lavado_detallado": "lavado", "fotos_publicacion": "fotos"}
COSTO_CAPITAL_DIA = 0.015 / 30          # 1,5 % mensual
PESO_LIQUIDEZ = {"alta": 1.3, "media": 1.0, "baja": 0.7}


def _prioridad(carro: dict, pendiente: list[dict]) -> float:
    dias = sum(t["dias"] for t in pendiente) or 1
    return carro["precio_compra"] * COSTO_CAPITAL_DIA * PESO_LIQUIDEZ[carro["liquidez"]] / dias


def simular(carros: list[dict], politica: str, capacidad: dict | None = None) -> dict:
    """Simulación día a día del taller. politica = 'fifo' | 'agente'."""
    capacidad = capacidad or CAPACIDAD
    estado = {c["id"]: {"pendiente": [t for t in sorted(c["tareas"], key=lambda t: ORDEN.index(t["tarea"]))],
                        "en_curso": None, "resta": 0, "listo": None} for c in carros}
    por_id = {c["id"]: c for c in carros}
    dia = 0
    while any(e["listo"] is None for e in estado.values()) and dia < 200:
        # 1. terminar trabajos del día anterior
        for cid, e in estado.items():
            if e["en_curso"] and e["resta"] == 0:
                e["en_curso"] = None
                if not e["pendiente"]:
                    e["listo"] = dia
        # 2. asignar cupos libres
        ocupados = {a: sum(1 for e in estado.values() if e["en_curso"] == a) for a in capacidad}
        espera = [cid for cid, e in estado.items()
                  if e["listo"] is None and e["en_curso"] is None and e["pendiente"] and por_id[cid]["dia_compra"] <= dia]
        if politica == "agente":
            espera.sort(key=lambda cid: -_prioridad(por_id[cid], estado[cid]["pendiente"]))
        else:
            espera.sort(key=lambda cid: (por_id[cid]["dia_compra"], cid))
        for cid in espera:
            area = estado[cid]["pendiente"][0]["tarea"]
            if ocupados[area] < capacidad[area]:
                tarea = estado[cid]["pendiente"].pop(0)
                estado[cid]["en_curso"], estado[cid]["resta"] = area, tarea["dias"]
                ocupados[area] += 1
        # 3. avanzar un día
        for e in estado.values():
            if e["en_curso"]:
                e["resta"] -= 1
        dia += 1

    detalle, costo_capital, dias_tot = [], 0.0, 0
    for c in carros:
        dias = estado[c["id"]]["listo"] - c["dia_compra"]
        costo = c["precio_compra"] * COSTO_CAPITAL_DIA * dias
        costo_capital += costo
        dias_tot += dias
        detalle.append({"id": c["id"], "vehiculo": c["vehiculo"], "liquidez": c["liquidez"],
                        "dia_listo": estado[c["id"]]["listo"], "dias_en_taller": dias, "costo_capital": round(costo, -3)})
    alta = [d["dias_en_taller"] for d in detalle if d["liquidez"] == "alta"]
    return {
        "dias_promedio": round(dias_tot / len(carros), 1),
        "dias_promedio_liquidez_alta": round(sum(alta) / len(alta), 1) if alta else None,
        "ultimo_listo_dia": max(d["dia_listo"] for d in detalle),
        "costo_capital": round(costo_capital, -3),
        "detalle": sorted(detalle, key=lambda d: d["dia_listo"]),
    }


def analizar(carros: list[dict]) -> dict:
    base, agente = simular(carros, "fifo"), simular(carros, "agente")
    sobrecostos = []
    for c in carros:
        costo = sum(t["costo"] for t in c["tareas"])
        if costo > c["presupuesto_alistamiento"]:
            sobrecostos.append({"id": c["id"], "vehiculo": c["vehiculo"], "costo": costo,
                                "presupuesto": c["presupuesto_alistamiento"],
                                "exceso": costo - c["presupuesto_alistamiento"],
                                "tareas": [NOMBRE[t["tarea"]] for t in c["tareas"] if t["costo"]]})
    sobrecostos.sort(key=lambda s: -s["exceso"])
    carga = {NOMBRE[a]: sum(t["dias"] for c in carros for t in c["tareas"] if t["tarea"] == a) / CAPACIDAD[a]
             for a in ORDEN}
    cuello = max(carga, key=carga.get)
    # Escenario recomendado: un cupo más en el área cuello de botella
    # (p. ej. un taller de pintura aliado), con la misma regla de prioridad
    area_cuello = next(a for a in ORDEN if NOMBRE[a] == cuello)
    ampliado = simular(carros, "agente", {**CAPACIDAD, area_cuello: CAPACIDAD[area_cuello] + 1})
    primeros = [d["vehiculo"] for d in agente["detalle"][:3]]
    return {
        "carros": len(carros),
        "linea_base": {k: v for k, v in base.items() if k != "detalle"},
        "agente": {k: v for k, v in agente.items() if k != "detalle"},
        "ahorro": {
            "dias_promedio": round(base["dias_promedio"] - agente["dias_promedio"], 1),
            "costo_capital": base["costo_capital"] - agente["costo_capital"],
        },
        "escenario_cupo_extra": {
            "area": cuello,
            **{k: v for k, v in ampliado.items() if k != "detalle"},
            "ahorro_vs_base_dias": round(base["dias_promedio"] - ampliado["dias_promedio"], 1),
            "ahorro_vs_base_costo_capital": base["costo_capital"] - ampliado["costo_capital"],
        },
        "plan": agente["detalle"],
        "sobrecostos": sobrecostos,
        "cuello_botella": {"area": cuello, "dias_de_trabajo_por_cupo": round(carga[cuello], 1)},
        "recomendacion": (
            f"Alistar primero {', '.join(primeros)}. El cuello de botella es {cuello} "
            f"({carga[cuello]:.0f} días de trabajo por cupo): un segundo cupo ahí acelera todo el flujo. "
            f"{len(sobrecostos)} carro(s) superan el presupuesto de alistamiento que se usó al comprarlos: revisar el peritaje de compra."
        ),
        "supuestos": "Costo del capital 1,5 % mensual; capacidades por área: "
                     + ", ".join(f"{NOMBRE[a]} {n}" for a, n in CAPACIDAD.items()) + " carros a la vez.",
    }
