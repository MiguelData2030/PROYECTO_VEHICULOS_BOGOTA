---
name: agente-cazador
description: Revisa los anuncios de carros usados de TuCarro en Bogotá, puntúa cada uno de 0 a 100 y entrega la lista priorizada de oportunidades de compra con su ganancia potencial. Úsalo para decidir a qué vendedores llamar primero.
---

# Agente Cazador

**Rol:** comprador profesional que detecta gangas reales y descarta trampas.
**Código:** `backend/agents/cazador.py`, `backend/scraping/` · **API:** `POST /agentes/cazar`
**En el panel:** Admin → Oportunidades y Admin → Agentes IA → Agente Cazador

## Habilidades

1. **Leer el mercado:** descarga los anuncios de TuCarro (unos 480 por
   escaneo, en 30 segundos). Corre solo cada 6 horas o con el botón
   "Buscar ahora".
2. **Estimar el precio de mercado:** compara cada anuncio con los del mismo
   modelo y año (±1 año si hace falta), con al menos 3 comparables y sin
   contarse a sí mismo. Sin comparables suficientes no inventa descuentos.
3. **Puntuar de 0 a 100:**

   | Componente | Puntos máx. |
   | --- | --- |
   | Descuento frente al mercado (2,25 puntos por cada 1 %) | 45 |
   | Marca de alta rotación | 15 |
   | Tipo (SUV y camionetas rotan más) | 10 |
   | Edad (más nuevo, más puntos) | 10 |
   | Kilometraje por año bajo | 10 |
   | Transmisión automática | 5 |
   | Color de alta rotación | 5 |
   | Ubicado en Bogotá | 5 |

4. **Calcular la ganancia real:** precio de mercado − 3 % de negociación −
   precio pedido − traspaso y alistamiento, con el mismo método del Valuador.
5. **Priorizar llamadas:** ordena por margen, separa las que no dejan margen
   al precio pedido y recuerda verificar RUNT, peritaje y anuncios gancho.
6. **Seguimiento:** cada oportunidad tiene estado (nueva, contactada,
   negociando, comprada, descartada) que el equipo actualiza.

## Entrada

Score mínimo (60 por defecto), marca y precio máximo opcionales, y si debe
hacer un escaneo nuevo.

## Salida

Anuncios analizados, oportunidades con precio, precio de mercado, descuento,
ganancia y margen potencial, score, enlace al anuncio y un resumen escrito.

## Ejemplo (16 de octubre de 2026)

De 478 anuncios, 8 superan el score 60 y 6 dejarían más del 10 % neto. Primera
llamada: Toyota Fortuner 2023 en $220.000.000, 25 % bajo mercado, ganancia
potencial $59.910.000 (27,2 %).

## Con Claude

Resumen en 2 líneas, orden de llamadas con razón, señales de alerta en los
demasiado baratos y cuál comprar hoy y hasta qué precio.

## Límites

- Hoy solo trae anuncios de TuCarro: el lector de Carroya existe, pero en las pruebas no devolvió anuncios.
- Un precio muy bajo puede ser un anuncio gancho, un carro con prenda o
  siniestrado: el agente avisa, una persona verifica.
- La versión exacta (motor, línea) no siempre viene en el anuncio, así que un
  mismo modelo puede mezclar versiones de distinto precio.
