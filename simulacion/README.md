# Simulación de agentes nuevos

Mide los 4 agentes de operación contra una línea base (cómo se haría sin
agente), con datos simulados. Son los mismos agentes del panel web:

| Agente | Código | Skill |
| --- | --- | --- |
| Logística | `backend/agents/logistica.py` | `skills/logistica/SKILL.md` |
| Alistamiento | `backend/agents/alistamiento.py` | `skills/alistamiento/SKILL.md` |
| Crédito | `backend/agents/credito.py` | `skills/credito/SKILL.md` |
| Atención 24/7 | `backend/agents/atencion.py` | `skills/atencion/SKILL.md` |

## Ejecutar

Desde la raíz del proyecto, con las dependencias instaladas (`pip install -r requirements.txt`):

```bash
python simulacion/run.py
```

- `backend/agents/datos_simulados.py` genera los datos con semilla fija (2026): siempre los mismos números.
  Esta simulación usa el inventario de ejemplo; el panel web usa el inventario real.
- `data/` guarda los datos simulados (citas, carros por alistar, solicitudes de
  crédito, mensajes, inventario).
- `resultados/` guarda el resultado de cada agente (`.json`) y `resumen.md`.

Cada agente se compara con una línea base (cómo se haría sin agente) para
medir la mejora. Los supuestos de cada uno están al final de `resumen.md`.
