"""
Agente de Crédito — precalifica a cada comprador que pide financiación y, si
no le alcanza, busca cómo sí: más plazo, más cuota inicial u otro carro del
inventario que quepa en su capacidad de pago.

Reglas (editables, típicas de los bancos y financieras en Colombia):
  - Tasa efectiva anual según el puntaje del buró de crédito.
  - Todas las cuotas del cliente (las que ya paga + la del carro) no pueden
    pasar del 40 % de su ingreso mensual (35 % para independientes).
  - Financiación máxima: 90 % del valor del carro; plazo de 48 a 72 meses.
  - Puntaje menor a 550: no se presenta al banco (se ofrece plan de ahorro).

Línea base: el asesor revisa solo el plazo estándar de 60 meses con la cuota
inicial que el cliente ofrece; si no alcanza, el cliente se va.
"""

from __future__ import annotations

TASAS = [(750, 0.165), (650, 0.195), (550, 0.24)]  # puntaje mínimo → tasa E.A.
PLAZOS = [48, 60, 72]
PLAZO_ESTANDAR = 60
LIMITE_ENDEUDAMIENTO = {"empleado": 0.40, "pensionado": 0.40, "independiente": 0.35}
FINANCIACION_MAX = 0.90
INICIAL_EXTRA_MAX = 0.15   # cuánto más de inicial (sobre el precio) se le puede proponer


def tasa_ea(puntaje: int) -> float | None:
    return next((t for minimo, t in TASAS if puntaje >= minimo), None)


def cuota(monto: float, ea: float, meses: int) -> float:
    i = (1 + ea) ** (1 / 12) - 1
    return monto * i / (1 - (1 + i) ** -meses)


def monto_maximo(cuota_max: float, ea: float, meses: int) -> float:
    i = (1 + ea) ** (1 / 12) - 1
    return cuota_max * (1 - (1 + i) ** -meses) / i


def _cop(v: float) -> str:
    return f"${v:,.0f}".replace(",", ".")


def evaluar(s: dict, inventario: list[dict]) -> dict:
    ea = tasa_ea(s["puntaje_buro"])
    capacidad = s["ingreso_mensual"] * LIMITE_ENDEUDAMIENTO[s["empleo"]] - s["cuotas_actuales"]
    base = {"id": s["id"], "cliente": s["cliente"], "vehiculo": s["vehiculo"], "precio": s["precio"],
            "puntaje_buro": s["puntaje_buro"], "capacidad_cuota": round(max(0, capacidad), -3)}

    if ea is None or capacidad <= 0:
        motivo = "puntaje de buró bajo" if ea is None else "ya usa toda su capacidad de endeudamiento"
        return {**base, "decision": "no_viable", "linea_base_aprueba": False,
                "propuesta": f"No presentar al banco ({motivo}). Ofrecer plan de ahorro o compra de contado."}

    financiar = s["precio"] - s["cuota_inicial"]
    financiar_max = s["precio"] * FINANCIACION_MAX
    linea_base = financiar <= financiar_max and cuota(financiar, ea, PLAZO_ESTANDAR) <= capacidad

    # 1. tal como lo pide, con el plazo más corto que le alcance
    for meses in PLAZOS:
        c = cuota(financiar, ea, meses)
        if financiar <= financiar_max and c <= capacidad:
            return {**base, "decision": "aprobable", "linea_base_aprueba": linea_base, "tasa_ea": ea,
                    "plazo": meses, "cuota": round(c, -3), "cuota_inicial": s["cuota_inicial"],
                    "propuesta": f"Presentar a {meses} meses: cuota {_cop(round(c, -3))} "
                                 f"con inicial de {_cop(s['cuota_inicial'])}."}

    # 2. con más cuota inicial (a 72 meses)
    posible = min(financiar_max, monto_maximo(capacidad, ea, PLAZOS[-1]))
    inicial_necesaria = s["precio"] - posible
    if inicial_necesaria - s["cuota_inicial"] <= s["precio"] * INICIAL_EXTRA_MAX:
        inicial = round(inicial_necesaria + 50_000, -5)
        c = cuota(s["precio"] - inicial, ea, PLAZOS[-1])
        return {**base, "decision": "aprobable_con_ajuste", "linea_base_aprueba": False, "tasa_ea": ea,
                "plazo": PLAZOS[-1], "cuota": round(c, -3), "cuota_inicial": inicial,
                "propuesta": f"Subir la inicial a {_cop(inicial)} (+{_cop(inicial - s['cuota_inicial'])}) "
                             f"y financiar a 72 meses: cuota {_cop(round(c, -3))}. "
                             "Opción: recibir su carro actual como parte de la inicial."}

    # 3. otro carro del inventario que sí le alcance, con la misma inicial
    tope = min(s["cuota_inicial"] + monto_maximo(capacidad, ea, PLAZOS[-1]),
               s["cuota_inicial"] / (1 - FINANCIACION_MAX))
    opciones = sorted((v for v in inventario if v["precio"] <= tope), key=lambda v: -v["precio"])
    if opciones:
        v = opciones[0]
        c = cuota(v["precio"] - s["cuota_inicial"], ea, PLAZOS[-1])
        return {**base, "decision": "alternativa", "linea_base_aprueba": False, "tasa_ea": ea,
                "plazo": PLAZOS[-1], "cuota": round(c, -3), "cuota_inicial": s["cuota_inicial"],
                "alternativa": f"{v['marca']} {v['modelo']} {v['año']}", "precio_alternativa": v["precio"],
                "propuesta": f"El {s['vehiculo']} no le alcanza. Ofrecer el {v['marca']} {v['modelo']} {v['año']} "
                             f"({_cop(v['precio'])}): cuota {_cop(round(c, -3))} a 72 meses."}

    return {**base, "decision": "no_viable", "linea_base_aprueba": False, "tasa_ea": ea,
            "propuesta": "Su capacidad de pago no alcanza para ningún carro del inventario con esa inicial."}


def analizar(solicitudes: list[dict], inventario: list[dict]) -> dict:
    resultados = [evaluar(s, inventario) for s in solicitudes]
    cuenta = {d: sum(1 for r in resultados if r["decision"] == d)
              for d in ("aprobable", "aprobable_con_ajuste", "alternativa", "no_viable")}
    viables = [r for r in resultados if r["decision"] != "no_viable"]
    base = [r for r in resultados if r["linea_base_aprueba"]]
    valor = lambda r: r.get("precio_alternativa", r["precio"])
    return {
        "solicitudes": len(solicitudes),
        "decisiones": cuenta,
        "linea_base": {"ventas_viables": len(base), "valor_cop": sum(r["precio"] for r in base)},
        "agente": {"ventas_viables": len(viables), "valor_cop": sum(valor(r) for r in viables)},
        "ventas_rescatadas": len(viables) - len(base),
        "valor_rescatado_cop": sum(valor(r) for r in viables) - sum(r["precio"] for r in base),
        "detalle": resultados,
        "recomendacion": (
            f"De {len(solicitudes)} solicitudes, {len(viables)} pueden terminar en venta "
            f"({cuenta['aprobable']} tal cual, {cuenta['aprobable_con_ajuste']} subiendo la inicial y "
            f"{cuenta['alternativa']} con otro carro). Con solo el plazo estándar serían {len(base)}."
        ),
        "supuestos": "Tasas E.A.: 16,5 % (puntaje ≥ 750), 19,5 % (≥ 650), 24 % (≥ 550); endeudamiento máximo "
                     "40 % del ingreso (35 % independientes); financiación hasta el 90 %; plazos 48 a 72 meses. "
                     "Es una precalificación: la aprobación final es del banco.",
    }
