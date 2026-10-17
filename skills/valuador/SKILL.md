---
name: agente-valuador
description: Valora un carro usado en Bogotá y dice cuánto vale, cuánto pagar como máximo, en cuánto publicarlo y si conviene comprarlo (semáforo comprar / negociar / no comprar). Úsalo antes de hacer una oferta de compra a un particular o al evaluar un anuncio del mercado.
---

# Agente Valuador

**Rol:** perito comercial experto en el mercado colombiano de usados.
**Código:** `backend/agents/valuador.py` · **API:** `POST /agentes/valuar`
**En el panel:** Admin → Agentes IA → Agente Valuador

## Habilidades

1. **Encontrar comparables:** busca en los anuncios de TuCarro el mismo modelo
   con ±1 año (±2 si hay pocos), descarta precios absurdos (menos de la mitad
   o más del doble de la mediana) y excluye el propio anuncio.
2. **Ajustar por diferencias:** corrige cada comparable por kilometraje
   (0,8 % por cada 10.000 km, tope ±12 %) y por año de modelo (6 % por año).
3. **Estimar sin comparables:** si hay menos de 3, usa un modelo de
   depreciación: precio nuevo × retención de la marca × edad × kilometraje.
4. **Leer el carro:** suma o resta según estado mecánico (+3 % excelente,
   −8 % regular), número de dueños (−3 % con 3 o más) y color (−2 % si rota lento).
   Lista factores a favor y en contra (híbrido sin pico y placa, automático, marca).
5. **Hacer las cuentas del negocio:** costos de traspaso y alistamiento,
   precio de publicación, compra ideal y compra máxima.
6. **Dar un veredicto:** con el precio que pide el vendedor, semáforo verde
   (comprar), amarillo (negociar, con cifra de oferta y tope) o rojo (no comprar).
7. **Recordar la historia:** cuántos de ese modelo se han vendido, a qué margen
   y en cuántos días.

## Reglas expertas

| Regla | Valor |
| --- | --- |
| Margen neto mínimo sobre la compra | 10 % |
| Descuento típico al vender | 3 % |
| Costos estimados | $650.000 + 0,4 % del valor (traspaso) + 1,5 % (alistamiento; 3,5 % si el estado es regular) |
| Compra ideal | el menor entre la compra máxima y el 82 % del valor de mercado |
| Liquidez alta | 12 o más comparables, o marca de alta rotación con 4 o más |

## Entrada

Marca, modelo, año, kilometraje; opcionales: transmisión, combustible, color,
tipo, estado mecánico, número de dueños, precio pedido, URL del anuncio.

## Salida

Valor de mercado y rango, precio de venta sugerido, compra ideal y máxima,
costos, margen esperado, días estimados de venta, liquidez, semáforo,
veredicto, factores, comparables, historial y un análisis escrito.

## Ejemplo

Mazda CX-5 2021, 50.000 km, el vendedor pide $95.000.000:
valor de mercado $114.300.000, compra máxima $98.300.000 →
**"NEGOCIAR: ofrece 93.500.000 y no pases de 98.300.000."**

## Con Claude

Claude recibe el cálculo y agrega: lectura del precio, fallas típicas del
modelo a revisar en el peritaje, estrategia de negociación y recomendación.

## Límites

- Depende de que el Cazador haya traído anuncios del modelo; sin ellos usa el
  modelo de depreciación (menos preciso).
- No ve el carro: el estado mecánico lo informa quien lo revisó.
- No consulta RUNT ni prendas; eso se verifica antes de pagar.
