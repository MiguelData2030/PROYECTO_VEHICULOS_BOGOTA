---
name: agente-credito
description: Precalifica a un comprador que quiere financiar un carro - calcula la cuota con la tasa según su puntaje de buró y su capacidad de pago, y si no le alcanza busca cómo sí - más plazo, más cuota inicial u otro carro del inventario. Úsalo cuando un cliente pregunta por financiación, antes de enviar la solicitud al banco.
---

# Agente de Crédito (nuevo, simulado)

**Rol:** asesor de financiación que busca el camino para cerrar la venta.
**Código:** `simulacion/agentes/credito.py` · **Datos de prueba:** `simulacion/data/credito.json`

## Habilidades

1. **Calcular la cuota:** sistema francés con la tasa mensual equivalente a la
   tasa efectiva anual.
2. **Medir la capacidad de pago:** todas las cuotas del cliente no pueden pasar
   del 40 % de su ingreso (35 % si es independiente).
3. **Decidir en 4 niveles:**

   | Decisión | Cuándo |
   | --- | --- |
   | Aprobable | Le alcanza tal cual, con el plazo más corto posible (48, 60 o 72 meses) |
   | Aprobable con ajuste | Le alcanza a 72 meses subiendo la inicial hasta 15 % del precio (o con su carro en parte de pago) |
   | Alternativa | Otro carro del inventario cabe en su capacidad con la misma inicial |
   | No viable | Puntaje menor a 550 o sin capacidad de pago: plan de ahorro o contado |

4. **Explicar la propuesta** en una frase lista para decirle al cliente.

## Reglas (editables)

| Puntaje de buró | Tasa E.A. |
| --- | --- |
| 750 o más | 16,5 % |
| 650 a 749 | 19,5 % |
| 550 a 649 | 24 % |
| Menos de 550 | no se presenta |

Financiación máxima 90 % del precio · plazos 48, 60 y 72 meses.

## Salida

Por solicitud: decisión, tasa, plazo, cuota, cuota inicial, alternativa y
propuesta. En total: ventas viables y valor frente a la línea base.

## Resultado de la simulación (25 solicitudes)

| | Solo plazo estándar (60 meses) | Agente |
| --- | --- | --- |
| Ventas viables | 7 | 18 |
| Valor | $598.500.000 | $1.597.400.000 |

De las 18: 10 tal cual, 2 subiendo la inicial y 6 con otro carro. 7 no son
viables. Ejemplo: "El Toyota Fortuner 2020 no le alcanza. Ofrecer el Mazda CX-30
2023 ($121.500.000): cuota $1.966.000 a 72 meses."

## Límites

- Es una precalificación: la aprobación final la da el banco o la financiera.
- Las tasas cambian: deben actualizarse cada mes con las de los aliados.
- Requiere autorización del cliente para consultar su puntaje (Ley 1266 y Ley 1581).
