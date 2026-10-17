"""
Ejecuta la simulación de los 4 agentes nuevos y guarda los resultados.

    python simulacion/run.py

Genera los datos simulados en simulacion/data/, los resultados de cada agente
en simulacion/resultados/<agente>.json y un resumen en
simulacion/resultados/resumen.md. Los agentes son los mismos que usa la API
(backend/agents/), en su versión de cálculo puro: no necesitan base de datos.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent))

from backend.agents import alistamiento, atencion, credito, logistica  # noqa: E402
from backend.agents import datos_simulados as datos  # noqa: E402

RESULTADOS = AQUI / "resultados"
DATA = AQUI / "data"


def _cop(v: float) -> str:
    return f"${v:,.0f}".replace(",", ".")


def main() -> dict:
    d = datos.generar()
    DATA.mkdir(exist_ok=True)
    for clave, valor in d.items():
        (DATA / f"{clave}.json").write_text(json.dumps(valor, ensure_ascii=False, indent=2), encoding="utf-8")
    res = {
        "logistica": logistica.analizar(d["sede"], d["citas"]),
        "alistamiento": alistamiento.analizar(d["alistamiento"]),
        "credito": credito.analizar(d["credito"], d["inventario"]),
        "atencion": atencion.analizar(d["mensajes"], d["inventario"]),
    }
    RESULTADOS.mkdir(exist_ok=True)
    for nombre, r in res.items():
        (RESULTADOS / f"{nombre}.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")

    lo, al, cr, at = res["logistica"], res["alistamiento"], res["credito"], res["atencion"]
    esc = al["escenario_cupo_extra"]
    resumen = f"""# Resultados de la simulación — agentes nuevos de AutoNegocio

Datos 100 % simulados (semilla {datos.SEMILLA}); cada ejecución da los mismos números.

| Agente | Sin agente | Con agente | Ganancia |
| --- | --- | --- | --- |
| Logística ({lo['citas']} citas, {lo['conductores']} conductores) | {lo['linea_base']['km']} km, {lo['linea_base']['horas_conductor']} h, {lo['linea_base']['citas_tarde']} llegadas tarde | {lo['agente']['km']} km, {lo['agente']['horas_conductor']} h, {lo['agente']['citas_tarde']} llegadas tarde | {lo['ahorro']['km_pct']} % menos km; {_cop(lo['ahorro']['costo_mes_cop'])} al mes |
| Alistamiento ({al['carros']} carros) | {al['linea_base']['dias_promedio']} días en taller; capital parado {_cop(al['linea_base']['costo_capital'])} | {esc['dias_promedio']} días con un cupo más en {esc['area']}; {_cop(esc['costo_capital'])} | {esc['ahorro_vs_base_dias']} días menos por carro; {_cop(esc['ahorro_vs_base_costo_capital'])} menos de capital parado |
| Crédito ({cr['solicitudes']} solicitudes) | {cr['linea_base']['ventas_viables']} ventas posibles ({_cop(cr['linea_base']['valor_cop'])}) | {cr['agente']['ventas_viables']} ventas posibles ({_cop(cr['agente']['valor_cop'])}) | {cr['ventas_rescatadas']} ventas rescatadas |
| Atención ({at['mensajes']} mensajes) | primera respuesta en {at['tiempo_respuesta']['asesor_min']} min | {at['resueltos_automaticamente']} respondidos en 1 min | {at['resueltos_pct']} % sin intervención; {at['leads_calientes']} leads calientes |

## Recomendaciones de cada agente

- **Logística:** {lo['recomendacion']}
- **Alistamiento:** {al['recomendacion']}
- **Crédito:** {cr['recomendacion']}
- **Atención:** {at['recomendacion']}

## Supuestos

- Logística: {lo['supuestos']}
- Alistamiento: {al['supuestos']}
- Crédito: {cr['supuestos']}
- Atención: {at['supuestos']}
"""
    (RESULTADOS / "resumen.md").write_text(resumen, encoding="utf-8")
    return res


if __name__ == "__main__":
    main()
    print((RESULTADOS / "resumen.md").read_text(encoding="utf-8"))
