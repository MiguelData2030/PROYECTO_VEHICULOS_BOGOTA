---
name: agente-atencion
description: Da la primera respuesta a los mensajes de WhatsApp, Instagram, Facebook, TikTok y la web a cualquier hora - entiende si el cliente quiere comprar, vender, financiar, saber si un carro está disponible, agendar una cita o quejarse, responde con el inventario real, marca los leads calientes y pasa a una persona las quejas y lo que no entiende. Úsalo como primer filtro de todos los mensajes entrantes.
---

# Agente de Atención 24/7 (nuevo, simulado)

**Rol:** asesor de primera línea que nunca deja un mensaje sin respuesta.
**Código:** `simulacion/agentes/atencion.py` · **Datos de prueba:** `simulacion/data/mensajes.json`

## Habilidades

1. **Entender la intención:** comprar, vender, financiación, disponibilidad,
   cita, queja u otro, con un nivel de confianza.
2. **Sacar los datos del mensaje:** marca, tipo de carro, presupuesto
   ("80 millones"), ingreso ("gano 6 millones") y urgencia ("esta semana",
   "de contado").
3. **Responder con datos reales:** carros del inventario que encajan con marca,
   tipo y presupuesto, con kilometraje y precio; enlace al cotizador para quien
   vende; capacidad de financiación estimada para quien da su ingreso.
4. **Calificar el lead:** caliente (presupuesto + preferencia o urgencia),
   tibio o frío, para que el asesor llame primero a los calientes.
5. **Escalar a una persona:** quejas y mensajes con baja confianza.

## Salida

Por mensaje: intención, datos extraídos, respuesta, temperatura y si pasa a
una persona. En total: precisión, resueltos sin persona, fuera de horario y
leads calientes.

## Resultado de la simulación (40 mensajes de un día)

| Indicador | Valor |
| --- | --- |
| Intención bien detectada | 95 % (38 de 40) |
| Respondidos sin una persona | 33 (82,5 %), en menos de 1 minuto |
| Llegaron fuera del horario | 10 |
| Leads calientes marcados | 15 |
| Pasados a una persona | 7 (5 quejas y 2 mensajes dudosos) |

Línea base: un asesor tarda 47 minutos en promedio en la primera respuesta (supuesto).

## Cómo funciona en producción

En la simulación la intención se detecta con palabras clave. En producción,
Claude clasifica el mensaje y redacta la respuesta con el inventario real, y
las palabras clave quedan como respaldo, igual que en los 5 agentes actuales.
Se conecta con la API de WhatsApp Business y crea el lead en el CRM.

## Límites

- La precisión del 95 % es sobre mensajes simulados; con mensajes reales será
  menor con palabras clave y mayor con Claude.
- No negocia precios ni promete descuentos: eso lo hace una persona.
- Las quejas siempre van a una persona.
