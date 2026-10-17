# Resultados de la simulación — agentes nuevos de AutoNegocio

Datos 100 % simulados (semilla 2026); cada ejecución da los mismos números.

| Agente | Sin agente | Con agente | Ganancia |
| --- | --- | --- | --- |
| Logística (18 citas, 2 conductores) | 191.2 km, 25.3 h, 5 llegadas tarde | 108.0 km, 19.7 h, 0 llegadas tarde | 43.5 % menos km; $4.246.000 al mes |
| Alistamiento (14 carros) | 8.9 días en taller; capital parado $4.322.000 | 6.9 días con un cupo más en latonería y pintura; $3.267.000 | 2.0 días menos por carro; $1.055.000 menos de capital parado |
| Crédito (25 solicitudes) | 7 ventas posibles ($598.500.000) | 18 ventas posibles ($1.597.400.000) | 11 ventas rescatadas |
| Atención (40 mensajes) | primera respuesta en 47 min | 33 respondidos en 1 min | 82.5 % sin intervención; 15 leads calientes |

## Recomendaciones de cada agente

- **Logística:** Con 2 conductores las 18 citas se cubren en 108.0 km y 19.7 horas, con 0 llegadas tarde (antes: 191.2 km, 25.3 horas y 5 llegadas tarde).
- **Alistamiento:** Alistar primero Mazda CX-5 2022, Toyota Corolla Cross 2022, Nissan Kicks 2021. El cuello de botella es latonería y pintura (21 días de trabajo por cupo): un cupo más ahí deja cada carro listo 2.0 días antes en promedio. 6 carro(s) superan el presupuesto de alistamiento que se usó al comprarlos: revisar el peritaje de compra.
- **Crédito:** De 25 solicitudes, 18 pueden terminar en venta (10 tal cual, 2 subiendo la inicial y 6 con otro carro). Con solo el plazo estándar serían 7.
- **Atención:** El agente respondió solo 33 de 40 mensajes en menos de 1 minuto, incluidos 10 que llegaron fuera del horario de atención. Detectó 15 leads calientes para que un asesor los llame primero y pasó 7 (quejas o mensajes dudosos) a una persona.

## Supuestos

- Logística: Velocidad 20 km/h; calles = línea recta × 1,35; $1.100 por km y $18.000 por hora de conductor; 22 días al mes; salida 08:00.
- Alistamiento: Costo del capital 1,5 % mensual; capacidades por área: mecánica 2, latonería y pintura 1, llantas 1, lavado 2, fotos 2 carros a la vez.
- Crédito: Tasas E.A.: 16,5 % (puntaje ≥ 750), 19,5 % (≥ 650), 24 % (≥ 550); endeudamiento máximo 40 % del ingreso (35 % independientes); financiación hasta el 90 %; plazos 48 a 72 meses. Es una precalificación: la aprobación final es del banco.
- Atención: Primera respuesta de un asesor: 47 minutos en promedio. La precisión se mide contra mensajes simulados; con mensajes reales será menor con palabras clave y mayor con Claude.
