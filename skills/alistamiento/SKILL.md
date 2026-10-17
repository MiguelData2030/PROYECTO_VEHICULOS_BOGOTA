---
name: agente-alistamiento
description: Organiza el taller de alistamiento de carros recién comprados - decide en qué orden pasan por mecánica, latonería y pintura, llantas, lavado y fotos para liberar capital lo antes posible, detecta el área que frena todo el flujo y avisa cuando un carro gasta más de lo presupuestado. Úsalo cada mañana al asignar el trabajo del taller.
---

# Agente de Alistamiento

**Rol:** jefe de taller que piensa en el capital parado, no solo en las tareas.
**Código:** `backend/agents/alistamiento.py` · **API:** `POST /agentes/alistamiento`
**En el panel:** Admin → Agentes IA → Agente Alistamiento: cupos por área ajustables, cronograma día por
día (Gantt) y sobrecostos. Los trabajos de taller son simulados sobre carros del inventario real.

## Habilidades

1. **Secuenciar el trabajo:** cada carro pasa por sus tareas en orden
   (mecánica → latonería y pintura → llantas → lavado → fotos) y cada área
   atiende un número limitado de carros a la vez.
2. **Priorizar por capital liberado:** atiende primero el carro con más
   costo diario de capital × liquidez ÷ días de taller pendientes (regla de
   programación "más peso por menor tiempo").
3. **Encontrar el cuello de botella:** calcula los días de trabajo por cupo de
   cada área y simula qué pasa si se agrega un cupo en la más cargada.
4. **Controlar el presupuesto:** compara el costo real del alistamiento con el
   que estimó el Agente Valuador al comprar ($650.000 + 1,9 % del precio) y
   lista los que se pasaron, para revisar el peritaje de compra.

## Supuestos (editables)

Costo del capital 1,5 % mensual · liquidez: alta ×1,3, media ×1,0, baja ×0,7 ·
capacidades: mecánica 2, latonería y pintura 1, llantas 1, lavado 2, fotos 2.

## Salida

Plan con el día en que cada carro queda listo, días en taller, costo de capital,
cuello de botella, escenario con un cupo extra y lista de sobrecostos.

## Resultado de la simulación (14 carros, 3 llegan por día)

| | Orden de llegada | Agente | Agente + 1 cupo en latonería |
| --- | --- | --- | --- |
| Días promedio en taller | 8,9 | 9,1 | 6,9 |
| Capital parado (costo) | $4.322.000 | $3.916.000 | $3.267.000 |
| Último carro listo (día) | 24 | 25 | 17 |

La regla de prioridad sola baja el costo del capital un 9 %; el mayor efecto
viene de lo que el agente detecta: latonería y pintura tiene 21 días de trabajo
por cupo. Con un taller aliado de pintura cada carro sale 2 días antes.
También marcó 6 carros cuyo alistamiento superó lo presupuestado.

## Siguiente paso

Registrar las órdenes de trabajo por carro (tarea, días, costo) en el
inventario y mostrar el plan del día en el panel.

## Uso en una empresa logística

Es la programación de recursos limitados (muelles de cargue, montacargas,
mantenimiento de vehículos) para sacar primero lo que más vale.
