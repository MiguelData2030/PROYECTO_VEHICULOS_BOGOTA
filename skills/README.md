# Skills de los agentes de AutoNegocio

Cada carpeta describe un agente: su rol, los datos que usa, sus habilidades,
las reglas expertas que aplica, lo que entrega y sus límites. Es el "manual de
cargo" del agente y sigue el formato de Agent Skills (`SKILL.md` con
encabezado `name` / `description`), así que también se puede cargar en Claude.

## Agentes

Los 9 agentes están en el panel (**Admin → Agentes IA**) y en la API (`/agentes/...`).

| Agente | Skill | Código |
| --- | --- | --- |
| Valuador | [valuador/SKILL.md](valuador/SKILL.md) | `backend/agents/valuador.py` |
| Cazador | [cazador/SKILL.md](cazador/SKILL.md) | `backend/agents/cazador.py` + `backend/scraping/` |
| Marketing (estrategia + piezas) | [marketing/SKILL.md](marketing/SKILL.md) | `backend/agents/marketing.py` |
| Financiero | [financiero/SKILL.md](financiero/SKILL.md) | `backend/agents/financiero.py` |
| Ventas | [ventas/SKILL.md](ventas/SKILL.md) | `backend/agents/ventas.py` |
| Atención 24/7 | [atencion/SKILL.md](atencion/SKILL.md) | `backend/agents/atencion.py` |
| Crédito | [credito/SKILL.md](credito/SKILL.md) | `backend/agents/credito.py` |
| Logística | [logistica/SKILL.md](logistica/SKILL.md) | `backend/agents/logistica.py` |
| Alistamiento | [alistamiento/SKILL.md](alistamiento/SKILL.md) | `backend/agents/alistamiento.py` |

Los 4 últimos trabajan con el inventario real y con datos de operación
simulados (citas, trabajos de taller, solicitudes y mensajes de ejemplo,
generados en `backend/agents/datos_simulados.py`). Para medirlos contra una
línea base sin agente:

```bash
python simulacion/run.py
```

## Cómo trabaja cualquier agente

1. **Datos:** lee la información del negocio (mercado, inventario, ventas, CRM).
2. **Reglas expertas:** aplica fórmulas revisables (márgenes, topes, prioridades).
3. **Cálculo propio:** produce cifras y una recomendación concreta.
4. **Claude (opcional):** si hay `ANTHROPIC_API_KEY`, redacta el análisis escrito.
   Si no hay clave o falla, el agente responde igual con su plantilla.

Las cifras siempre salen del paso 3. La IA generativa interpreta y explica,
nunca inventa los números. Los agentes recomiendan; una persona decide.
