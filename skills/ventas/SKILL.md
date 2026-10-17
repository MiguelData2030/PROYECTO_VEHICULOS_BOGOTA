---
name: agente-ventas
description: Trabaja el embudo del CRM como un jefe comercial - decide a quién contactar hoy y en qué orden, redacta el mensaje de WhatsApp de cada cliente y sugiere otros carros del inventario que caben en su presupuesto. Úsalo al empezar cada jornada comercial.
---

# Agente de Ventas

**Rol:** jefe comercial experto en leads de redes sociales y WhatsApp.
**Código:** `backend/agents/ventas.py` · **API:** `POST /agentes/ventas`
**En el panel:** Admin → Agentes IA → Agente Ventas (los datos vienen de Admin → CRM)

## Habilidades

1. **Priorizar:** da un puntaje a cada negocio abierto:

   | Señal | Puntos |
   | --- | --- |
   | Etapa: nuevo / contactado / cita / negociación | 30 / 20 / 35 / 45 |
   | Días sin contacto (5 por día) | hasta 25 |
   | Próxima acción vencida | 20 |
   | Valor del negocio (1 por cada $10 M) | hasta 15 |
   | Lead nuevo de redes o WhatsApp (se enfría en horas) | 10 |

2. **Explicar la razón:** "10 días sin contacto, está a un paso de cerrar".
3. **Decir la siguiente acción por etapa:** responder en menos de 1 hora,
   agendar test drive, confirmar cita, cerrar con abono. Para quien vende su
   carro: pedir fotos, agendar peritaje, enviar oferta, cerrar compra.
4. **Redactar el mensaje de WhatsApp** personalizado con el nombre y el carro.
5. **Ofrecer alternativas:** hasta 3 carros disponibles entre el 80 % y el 108 %
   del presupuesto del cliente, primero del mismo tipo.
6. **Medir el embudo:** negocios abiertos, vencidos, sin asesor, leads nuevos de
   redes y valor ponderado (nuevo 10 %, contactado 25 %, cita 45 %, negociación 70 %).

## Salida

Indicadores del embudo y la lista priorizada con cliente, teléfono, etapa,
canal, carro, valor, asesor, puntaje, razón, acción, mensaje y alternativas.

## Ejemplo

29 negocios abiertos por $538.895.000 ponderados, 2 vencidos. Primero:
Carlos Cárdenas Suárez, en negociación por un Mazda CX-5 2019, con 10 días sin
contacto.

## Con Claude

Plan de llamadas del día en orden, un consejo para cada uno de los 3 primeros y
el hábito comercial que conviene corregir según los datos.

## Límites

- Depende de que el equipo registre cada interacción en el CRM.
- No envía los mensajes: los deja listos para que el asesor los mande.
