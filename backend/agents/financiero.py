"""
Agente Financiero — cash flow, capital tied up in stock, price cuts for aged
units, profitability by brand/segment and a 3-month projection.

Assumptions (editable constants): cost of capital 1.5 % per month (bank or
partner financing of the inventory); minimum acceptable net margin 3 % when
cutting the price of an aged unit.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date, datetime
from typing import Optional

from sqlalchemy import select

from backend.models import Transaccion, Vehiculo
from backend.models.database import AsyncSessionLocal
from .base_agent import ask_claude

COSTO_CAPITAL_MENSUAL = 0.015
MARGEN_MINIMO_REBAJA = 0.03
META_MARGEN = 12.0
META_DIAS = 30

SYSTEM_PROMPT = """Eres el Agente Financiero de AutoNegocio, compraventa de usados en Bogotá.
Piensas como gerente financiero de concesionario: rotación de inventario, costo del capital,
margen neto y flujo de caja. Responde en español, en viñetas, máximo 200 palabras, con cifras
en COP y acciones concretas para este mes."""


def _d(v) -> Optional[date]:
    if v is None:
        return None
    return v.date() if isinstance(v, datetime) else v


def _mes(d: date) -> str:
    return f"{d.year}-{d.month:02d}"


def _cop(v) -> str:
    return f"${v:,.0f}".replace(",", ".") if v is not None else "N/D"


class AgenteFinanciero:
    async def analizar(self) -> dict:
        hoy = date.today()
        async with AsyncSessionLocal() as session:
            vehiculos = {v.id: v for v in (await session.execute(select(Vehiculo))).scalars().all()}
            txs = (await session.execute(select(Transaccion))).scalars().all()

        # ------------------------------------------------ monthly cash flow
        meses: dict[str, dict] = defaultdict(lambda: {"ingresos": 0.0, "egresos": 0.0, "ganancia": 0.0, "ventas": 0, "compras": 0})
        gastos_compra: dict[int, float] = defaultdict(float)
        for t in txs:
            if t.tipo == "compra":
                gastos_compra[t.vehiculo_id] += (t.gastos_traspaso or 0) + (t.gastos_reacondicionamiento or 0)
        for t in txs:
            m = meses[_mes(_d(t.fecha))]
            costos = (t.comision or 0) + (t.gastos_traspaso or 0) + (t.gastos_reacondicionamiento or 0)
            if t.tipo == "venta":
                m["ingresos"] += t.precio
                m["egresos"] += costos
                m["ventas"] += 1
                m["ganancia"] += t.ganancia_neta or 0
            else:
                m["egresos"] += t.precio + costos
                m["compras"] += 1
        claves = sorted(meses)[-6:]
        flujo = [{"mes": k, **meses[k], "flujo_neto": meses[k]["ingresos"] - meses[k]["egresos"]} for k in claves]

        # --------------------------------------------- stock & capital tied up
        stock = [v for v in vehiculos.values() if v.estado != "vendido" and v.precio_compra]
        tramos = {"0-30": [0, 0.0], "31-60": [0, 0.0], "61-90": [0, 0.0], "90+": [0, 0.0]}
        rebajas = []
        costo_mensual_stock = 0.0
        for v in stock:
            dias = (hoy - _d(v.fecha_compra)).days if v.fecha_compra else 0
            clave = "0-30" if dias <= 30 else "31-60" if dias <= 60 else "61-90" if dias <= 90 else "90+"
            tramos[clave][0] += 1
            tramos[clave][1] += v.precio_compra
            costo_dia = v.precio_compra * COSTO_CAPITAL_MENSUAL / 30
            costo_mensual_stock += costo_dia * 30
            if dias > 45 and v.precio_venta:
                corte = 0.03 if dias <= 60 else 0.05 if dias <= 90 else 0.08
                invertido = v.precio_compra + gastos_compra.get(v.id, 0)
                piso = invertido * (1 + MARGEN_MINIMO_REBAJA)
                nuevo = max(piso, v.precio_venta * (1 - corte))
                nuevo = round(nuevo / 500_000) * 500_000 - 100_000 if nuevo > 1_000_000 else nuevo
                if nuevo < v.precio_venta:
                    rebajas.append({
                        "vehiculo_id": v.id,
                        "vehiculo": f"{v.marca} {v.modelo} {v.año}",
                        "dias": dias,
                        "precio_actual": v.precio_venta,
                        "precio_sugerido": nuevo,
                        "rebaja_pct": round((v.precio_venta - nuevo) / v.precio_venta * 100, 1),
                        "margen_resultante_pct": round((nuevo - invertido) / invertido * 100, 1),
                        "costo_capital_acumulado": round(costo_dia * dias, -3),
                    })
        rebajas.sort(key=lambda r: -r["dias"])

        # ---------------------------------- profitability by brand & segment
        def rentabilidad(clave_fn) -> list[dict]:
            grupos: dict[str, list] = defaultdict(list)
            for t in txs:
                if t.tipo != "venta":
                    continue
                v = vehiculos.get(t.vehiculo_id)
                if not v or not v.precio_compra or not v.fecha_compra:
                    continue
                dias = max(1, (_d(t.fecha) - _d(v.fecha_compra)).days)
                grupos[clave_fn(v)].append((t.ganancia_neta or 0, v.precio_compra, dias))
            out = []
            for k, filas in grupos.items():
                ganancia = sum(f[0] for f in filas)
                margen = statistics.mean(f[0] / f[1] * 100 for f in filas)
                dias = statistics.mean(f[2] for f in filas)
                # Monthly return on the capital invested (profit / cost, per 30 days held)
                roi_mensual = statistics.mean((f[0] / f[1]) * (30 / f[2]) * 100 for f in filas)
                out.append({"grupo": k, "ventas": len(filas), "ganancia": ganancia, "margen_pct": round(margen, 1),
                            "dias_promedio": round(dias), "roi_mensual_pct": round(roi_mensual, 1)})
            return sorted(out, key=lambda x: -x["roi_mensual_pct"])

        por_marca = [m for m in rentabilidad(lambda v: v.marca) if m["ventas"] >= 2]
        por_segmento = rentabilidad(lambda v: v.tipo_vehiculo)

        # ------------------------------------------------ 3-month projection
        ult3 = flujo[-4:-1] if len(flujo) >= 4 else flujo  # skip the current (partial) month
        ventas_mes = statistics.mean(m["ventas"] for m in ult3) if ult3 else 0
        ganancia_mes = statistics.mean(m["ganancia"] for m in ult3) if ult3 else 0
        proyeccion = {
            "ventas_mes": round(ventas_mes, 1),
            "ganancia_mes": round(ganancia_mes, -5),
            "ganancia_trimestre": round(ganancia_mes * 3, -5),
        }

        ventas_12 = [t for t in txs if t.tipo == "venta" and (hoy - _d(t.fecha)).days <= 365]
        margenes = [t.ganancia_neta / vehiculos[t.vehiculo_id].precio_compra * 100
                    for t in ventas_12 if t.ganancia_neta is not None and vehiculos.get(t.vehiculo_id) and vehiculos[t.vehiculo_id].precio_compra]
        perdidas = [t for t in ventas_12 if (t.ganancia_neta or 0) < 0]
        capital = sum(v.precio_compra for v in stock)
        capital_viejo = tramos["61-90"][1] + tramos["90+"][1]

        alertas = []
        if capital and capital_viejo / capital > 0.2:
            alertas.append(f"{capital_viejo / capital * 100:.0f}% del capital está en carros con más de 60 días.")
        if margenes and statistics.mean(margenes) < META_MARGEN:
            alertas.append(f"Margen neto promedio {statistics.mean(margenes):.1f}%, por debajo de la meta del {META_MARGEN:.0f}%.")
        if perdidas:
            alertas.append(f"{len(perdidas)} venta(s) con pérdida en el último año: revisar peritaje de compra.")
        if flujo and flujo[-1]["flujo_neto"] < 0:
            alertas.append("El flujo de caja de este mes va negativo (se compró más de lo que se vendió).")

        resultado = {
            "flujo_caja": flujo,
            "capital_invertido": capital,
            "costo_capital_mensual": round(costo_mensual_stock, -3),
            "antiguedad_stock": [{"tramo": k, "vehiculos": v[0], "capital": v[1]} for k, v in tramos.items()],
            "rebajas_sugeridas": rebajas,
            "rentabilidad_marca": por_marca,
            "rentabilidad_segmento": por_segmento,
            "proyeccion": proyeccion,
            "margen_promedio_pct": round(statistics.mean(margenes), 1) if margenes else None,
            "alertas": alertas,
            "supuestos": f"Costo de capital {COSTO_CAPITAL_MENSUAL * 100:.1f}% mensual; las rebajas no bajan del {MARGEN_MINIMO_REBAJA * 100:.0f}% de margen.",
        }
        texto = await self._ia(resultado)
        resultado["analisis"] = texto or self._base(resultado)
        resultado["analisis_ia"] = texto is not None
        return resultado

    def _base(self, r: dict) -> str:
        lineas = []
        p = r["proyeccion"]
        lineas.append(f"Ritmo actual: {p['ventas_mes']} ventas/mes y {_cop(p['ganancia_mes'])} de ganancia neta mensual "
                      f"→ proyección del trimestre {_cop(p['ganancia_trimestre'])}.")
        lineas.append(f"Capital en inventario: {_cop(r['capital_invertido'])}; tenerlo parado cuesta unos "
                      f"{_cop(r['costo_capital_mensual'])} al mes.")
        if r["rentabilidad_marca"]:
            best = r["rentabilidad_marca"][0]
            worst = r["rentabilidad_marca"][-1]
            lineas.append(f"Donde más rinde el capital: {best['grupo']} ({best['roi_mensual_pct']}% de rendimiento mensual, "
                          f"se vende en {best['dias_promedio']} días). Menos eficiente: {worst['grupo']} ({worst['roi_mensual_pct']}% mensual).")
        if r["rebajas_sugeridas"]:
            lineas.append(f"Rebajar {len(r['rebajas_sugeridas'])} carro(s) con más de 45 días para liberar capital; "
                          f"empezar por {r['rebajas_sugeridas'][0]['vehiculo']} ({r['rebajas_sugeridas'][0]['dias']} días).")
        lineas += r["alertas"]
        return "\n".join(f"• {x}" for x in lineas)

    async def _ia(self, r: dict) -> Optional[str]:
        prompt = f"""Datos financieros de AutoNegocio:
- Flujo de caja últimos meses: {[(m['mes'], round(m['flujo_neto'] / 1e6, 1), m['ventas']) for m in r['flujo_caja']]} (mes, flujo neto en millones, ventas)
- Capital en inventario: {_cop(r['capital_invertido'])}; costo del capital: {_cop(r['costo_capital_mensual'])}/mes
- Antigüedad del stock: {r['antiguedad_stock']}
- Margen neto promedio 12 meses: {r['margen_promedio_pct']}%
- Rentabilidad por marca (rendimiento mensual del capital %, margen %, días): {[(m['grupo'], m['roi_mensual_pct'], m['margen_pct'], m['dias_promedio']) for m in r['rentabilidad_marca']]}
- Rentabilidad por segmento (rendimiento mensual %): {[(m['grupo'], m['roi_mensual_pct']) for m in r['rentabilidad_segmento']]}
- Rebajas sugeridas: {[(x['vehiculo'], x['dias'], x['rebaja_pct']) for x in r['rebajas_sugeridas']]}
- Proyección: {r['proyeccion']}
- Alertas: {r['alertas']}

Da: (1) diagnóstico en 2 líneas, (2) las 3 decisiones financieras más importantes de este mes,
(3) qué comprar más y qué evitar según el ROI, (4) un riesgo a vigilar."""
        return await ask_claude(prompt, system=SYSTEM_PROMPT)
