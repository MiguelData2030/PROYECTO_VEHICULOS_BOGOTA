# Simulación de agentes nuevos

Cuatro agentes propuestos para AutoNegocio, probados con datos simulados:

| Agente | Código | Skill |
| --- | --- | --- |
| Logística | `agentes/logistica.py` | `skills/logistica/SKILL.md` |
| Alistamiento | `agentes/alistamiento.py` | `skills/alistamiento/SKILL.md` |
| Crédito | `agentes/credito.py` | `skills/credito/SKILL.md` |
| Atención 24/7 | `agentes/atencion.py` | `skills/atencion/SKILL.md` |

## Ejecutar

Solo necesita Python 3.10 o superior (sin librerías adicionales):

```bash
python simulacion/run.py
```

- `datos.py` genera los datos con semilla fija (2026): siempre los mismos números.
- `data/` guarda los datos simulados (citas, carros por alistar, solicitudes de
  crédito, mensajes, inventario).
- `resultados/` guarda el resultado de cada agente (`.json`) y `resumen.md`.

Cada agente se compara con una línea base (cómo se haría sin agente) para
medir la mejora. Los supuestos de cada uno están al final de `resumen.md`.
