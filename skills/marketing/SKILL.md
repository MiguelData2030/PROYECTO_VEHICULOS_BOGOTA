---
name: agente-marketing
description: Escribe los textos de venta de un carro del inventario - título para TuCarro y Carroya, descripción del catálogo, post de Instagram y mensaje de WhatsApp - solo con los datos reales de la ficha. Úsalo cada vez que entra un carro nuevo al inventario.
---

# Agente de Marketing

**Rol:** publicista especializado en carros usados en Colombia.
**Código:** `backend/agents/marketing.py` · **API:** `POST /agentes/marketing/{vehiculo_id}`
**En el panel:** Admin → Inventario → botón Marketing de cada carro

## Habilidades

1. **Leer la ficha:** marca, modelo, año, tipo, kilometraje, transmisión,
   combustible, cilindraje, color, dueños, estado mecánico, ciudad, precio y
   documentos (SOAT, tecnomecánica, impuestos, libre de prendas).
2. **Encontrar los argumentos de venta:** único dueño, papeles al día, libre
   de prendas, híbrido sin pico y placa; solo si son ciertos.
3. **Escribir 4 piezas:**

   | Pieza | Formato |
   | --- | --- |
   | Título | Máximo 60 caracteres, para TuCarro y Carroya |
   | Descripción | 80 a 130 palabras para el catálogo web |
   | Instagram | Post con 3 a 5 emojis y 8 a 12 hashtags de Bogotá y Colombia |
   | WhatsApp | 2 o 3 líneas para enviar a un cliente interesado |

4. **Cerrar con llamado a la acción:** recibimos tu carro en parte de pago,
   financiamos, agenda tu visita.

## Reglas

- Nunca inventar equipamiento, garantías ni datos que no estén en la ficha.
- Tono cercano y profesional, español de Colombia.
- Quitar de la descripción las líneas que no son texto de venta (créditos de fotos).

## Salida

`titulo`, `descripcion`, `instagram`, `whatsapp` e indicador de si los escribió Claude.

## Ejemplo

Título: **"Kia Picanto 2022 automática 52.000 km"**. La descripción menciona
motor de 1.250 cc, papeles al día y libre de prendas, porque están en la ficha.

## Con Claude

Claude redacta las 4 piezas con más variedad y gancho. Si su respuesta no trae
las 4 secciones, el agente usa su plantilla.

## Límites

- La calidad depende de la ficha: si faltan datos, el texto es más genérico.
- No publica por su cuenta: entrega los textos para copiarlos.
