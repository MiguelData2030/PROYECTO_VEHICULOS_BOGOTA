---
name: agente-marketing
description: Gerente de marketing del negocio de carros usados - mide qué red social vende de verdad (del alcance al carro vendido), reparte el presupuesto de pauta del próximo mes hacia las redes que más venden, elige qué carros impulsar y a qué público, arma el calendario de contenido de la semana, detecta alertas y propone pruebas A/B. También escribe las piezas de cada carro (anuncio, descripción, post y WhatsApp). Úsalo cada lunes para planear la semana y cada mes para decidir la pauta.
---

# Agente de Marketing

**Rol:** gerente de marketing que piensa en ventas y margen, no en likes.
**Código:** `backend/agents/marketing.py`
**API:** `POST /agentes/marketing/estrategia?dias=90&presupuesto=` y `POST /agentes/marketing/{vehiculo_id}`
**En el panel:** Admin → Agentes IA → Agente Marketing (pestañas "Estrategia y presupuesto" y "Crear anuncios de un carro")

## Habilidades

1. **Medir el embudo de cada red** (Instagram, Facebook, TikTok, WhatsApp):
   alcance → leads → ventas del CRM → ganancia. Calcula costo por lead,
   conversión de lead a venta, costo por venta y retorno de la pauta
   (ganancia de los carros vendidos por cada peso invertido).
2. **Repartir el presupuesto del próximo mes:** mueve dinero hacia las redes
   que venden más por cada millón invertido, con un ajuste máximo de ±30 % por
   red, y reserva un 10 % para probar pauta en la red que ya trae clientes sin
   pagar. Estima leads y ventas esperadas con esa pauta.
3. **Elegir qué carros impulsar:** prioriza por días en inventario (50 %),
   margen (30 %) y tiempo sin publicarse (20 %). Para cada carro define:

   | Segmento | Público | Mensaje clave | Redes |
   | --- | --- | --- | --- |
   | Primer carro (hatchback o menos de $50 M) | 22 a 34 años | cuota baja, poco consumo | TikTok, Instagram |
   | Ciudad (sedán) | profesionales de 25 a 45 | economía, comodidad | Instagram, Facebook |
   | Familia (SUV) | familias de 30 a 50 | espacio, seguridad, financiación | Facebook, Instagram |
   | Ejecutivo (más de $120 M) | 35 a 55, alto poder adquisitivo | estatus, bajo kilometraje | Instagram, Facebook |
   | Trabajo (pick-up) | independientes y empresas | carga, financiación | Facebook |

   Dentro de las redes del segmento elige la que más leads trae por publicación
   y calcula la cuota mensual "desde" (20 % de inicial, 60 meses, 19,5 % E.A.).
4. **Armar el calendario de la semana:** 10 piezas repartidas según los leads
   de cada red, en el formato que mejor le funciona (reel, video, carrusel,
   historia, post) y en sus mejores días, sin repetir red el mismo día. Cada
   pieza trae su gancho listo para producir.
5. **Alertar:** leads de redes con más de 1 día sin respuesta (y cuánta venta
   ponen en riesgo), redes con costo por lead 1,4 veces el promedio, caída de
   engagement mayor al 20 %, formatos con 3 o más publicaciones sin leads y
   carros con más de 60 días en inventario.
6. **Proponer pruebas A/B:** por ejemplo, precio visible contra "cuota desde",
   o video con asesor contra solo el carro, con la métrica para decidir.
7. **Escribir las piezas de un carro** (habilidad de redacción): título de
   60 caracteres para TuCarro y Carroya, descripción para el catálogo, post de
   Instagram con hashtags de Bogotá y mensaje de WhatsApp, sin inventar datos.

## Datos que usa

Métricas diarias de cada red (alcance, interacciones, leads, inversión),
publicaciones con sus resultados (últimos 90 días como mínimo), negocios del
CRM por canal, ventas de los últimos 12 meses (ganancia por carro) e
inventario disponible con fechas de compra y precios.

## Salida

Embudo por red, presupuesto actual contra recomendado, leads y ventas
esperadas, carros a impulsar con público, mensaje, red y formato, calendario
semanal, alertas, pruebas A/B y un plan escrito.

## Ejemplo (datos demo, últimos 90 días)

Instagram vendió 7 carros con $2.925.000 de pauta: cada peso trajo 22,4 pesos
de ganancia. Facebook vendió 1 con $1.950.000. TikTok trajo 124 leads y 2 ventas
sin pauta. Plan del mes: Instagram +9 %, Facebook −40 % y prueba de $160.000 en
TikTok. Primer carro a impulsar: Mazda 2 Sedán 2022 (69 días en inventario,
margen de 26 %, nunca publicado) en reel de Instagram para profesionales de
25 a 45 años. Alerta: 3 leads de redes llevan más de 1 día sin respuesta.

## Con Claude

Claude recibe todo el cálculo y escribe el plan del gerente: diagnóstico, el
concepto de campaña del mes con nombre, las 3 movidas con cifras, qué dejar de
hacer y el indicador a revisar cada lunes. También redacta las piezas.

## Límites

- La venta se atribuye al canal donde nació el lead en el CRM: si el equipo no
  registra el canal, el retorno de cada red se distorsiona.
- Las horas de publicación son buenas prácticas para Bogotá: el sistema no
  guarda la hora de cada post.
- No publica ni compra pauta por su cuenta: entrega el plan y las piezas.
