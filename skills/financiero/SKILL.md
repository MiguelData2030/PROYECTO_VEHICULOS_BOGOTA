---
name: agente-financiero
description: Analiza la salud financiera del negocio de carros usados - flujo de caja mensual, capital parado en inventario y su costo, qué carros rebajar, rentabilidad por marca y segmento y proyección del trimestre. Úsalo en el cierre de cada semana o mes.
---

# Agente Financiero

**Rol:** gerente financiero de concesionario.
**Código:** `backend/agents/financiero.py` · **API:** `POST /agentes/financiero`
**En el panel:** Admin → Agentes IA → Agente Financiero

## Habilidades

1. **Flujo de caja:** por mes (últimos 6), ingresos por ventas menos compras,
   traspasos, alistamiento y comisiones.
2. **Capital parado:** cuánto dinero está en carros sin vender, por tramos de
   antigüedad (0-30, 31-60, 61-90 y más de 90 días), y cuánto cuesta al mes.
3. **Rebajas inteligentes:** para carros con más de 45 días propone un precio
   nuevo que nunca deja el margen por debajo del 3 %.

   | Días en inventario | Rebaja |
   | --- | --- |
   | 46 a 60 | 3 % |
   | 61 a 90 | 5 % |
   | Más de 90 | 8 % |

4. **Rentabilidad por marca y segmento:** ventas, ganancia, margen, días para
   vender y rendimiento mensual del capital (ganancia ÷ costo × 30 ÷ días).
5. **Proyección:** ventas y ganancia del mes y del trimestre con el promedio de
   los últimos 3 meses cerrados.
6. **Alertas:** más del 20 % del capital en carros de más de 60 días, margen
   promedio bajo la meta del 12 %, ventas con pérdida, flujo del mes negativo.

## Supuestos (editables)

Costo del capital 1,5 % mensual · margen mínimo al rebajar 3 % · meta de margen
12 % · meta de días para vender 30.

## Salida

Flujo de caja, capital invertido y su costo, antigüedad del stock, rebajas
sugeridas, rentabilidad por marca y segmento, proyección, alertas y análisis.

## Ejemplo

Con el año simulado detecta meses con flujo negativo (mayo de 2026:
−$52.170.000, porque se compraron 8 carros y se vendieron 6) y lo marca como
inversión en inventario, no como pérdida.

## Con Claude

Diagnóstico en 2 líneas, las 3 decisiones financieras del mes, qué comprar más
y qué evitar según el rendimiento, y un riesgo a vigilar.

## Límites

- Solo ve lo registrado en el sistema: gastos fuera de él (arriendo, nómina)
  no entran salvo que se registren.
- La proyección supone que los próximos meses se parecen a los últimos 3.
