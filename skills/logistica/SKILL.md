---
name: agente-logistica
description: Arma las rutas del día para peritajes a domicilio, entregas de carros vendidos y test drives en Bogotá - reparte las citas entre conductores por zona, respeta la ventana horaria de cada cliente y acorta los recorridos. Úsalo la noche anterior para planear el día siguiente.
---

# Agente de Logística (nuevo, simulado)

**Rol:** jefe de despacho que planea la ruta de cada conductor.
**Código:** `simulacion/agentes/logistica.py` · **Datos de prueba:** `simulacion/data/citas.json`

## Habilidades

1. **Repartir por zona:** ordena las citas por su ángulo alrededor de la sede y
   corta en sectores que equilibran el trabajo de cada conductor (tiempo de
   atención + ida y vuelta).
2. **Respetar ventanas horarias:** en cada paso elige la siguiente cita
   factible que deja menos tiempo muerto, dando prioridad a la que vence primero.
3. **Acortar la ruta:** prueba invertir tramos (2-opt) y se queda con el cambio
   solo si la ruta es más corta y no llega tarde a ningún cliente.
4. **Medir:** km, horas de conductor, esperas, llegadas tarde y costo del día,
   frente a la línea base (asignación en orden de llegada, conductores alternados).

## Supuestos (editables)

Velocidad promedio 20 km/h · distancia por calles = línea recta × 1,35 ·
$1.100 por km · $18.000 por hora de conductor · 22 días de operación al mes ·
2 conductores · salida 08:00 desde la sede.

## Entrada

Sede (coordenadas) y lista de citas: tipo (peritaje 45 min, entrega 60 min,
test drive 40 min), cliente, zona, coordenadas, ventana horaria.

## Salida

Ruta de cada conductor con hora de llegada por cita, km, hora de regreso,
esperas, llegadas tarde, comparación con la línea base y ahorro mensual.

## Resultado de la simulación (18 citas de un sábado, 2 conductores)

| | Sin agente | Con agente |
| --- | --- | --- |
| Kilómetros | 191,2 | 108,0 |
| Horas de conductor | 25,3 | 19,7 |
| Llegadas tarde | 5 | 0 |
| Costo del día | $666.000 | $473.000 |

Ahorro: 43,5 % de km y unos $4.246.000 al mes.

## Para llevarlo a producción

Tomar las citas del CRM (etapa "cita"), geocodificar direcciones (API de mapas)
y enviar la ruta a cada conductor por WhatsApp. Con tráfico real conviene usar
tiempos de una API de mapas en lugar de la velocidad promedio.

## Uso en una empresa logística

Es el mismo problema que el ruteo de una flota de reparto con ventanas de
entrega (VRPTW): solo cambian las citas por pedidos y los conductores por vehículos.
