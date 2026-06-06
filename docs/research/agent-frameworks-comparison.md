<!-- [C5-REAL] Exergy-Maximized -->
# Agent Frameworks — Competitive Analysis
> Generado: 2026-02-23 · Contexto: MOSKV-1 / CORTEX v5

---

## 📊 Tabla Comparativa

| Dimensión | OpenClaw | LangGraph | AutoGen | **CORTEX** |
|---|---|---|---|---|
| **Ejecución** | Local-first | Cloud/local | Cloud/local | **Local-first** |
| **Modelo** | Agnóstico | Agnóstico | Microsoft-ish | **Multi-LLM soberano** |
| **Persistencia** | SQLite local | LangSmith (cloud) | Ninguna nativa | **SQLite + CORTEX DB** |
| **Multi-agent** | Routing básico | Graph-based | Conversación | **Swarm Byzantine** |
| **Mensajería** | WA/TG/DC/Slack | ❌ | ❌ | ❌ *(pendiente)* |
| **Observabilidad** | Live Canvas | LangSmith traces | Logs básicos | **/mejoralo + X-Ray 13D** |
| **Plugin system** | Sí | Tools/chains | Skills | **Workflows + skills** |
| **Privacidad** | 🟢 100% local | 🟡 Depende | 🟡 Depende | 🟢 **100% local** |
| **Velocidad** | Media | Media | Lenta | 🚀 **Async-first** |

---

## 🏆 Puntuaciones (1–100)

| Framework | Score | Veredicto |
|---|---|---|
| **OpenClaw** | 71/100 🟡 | Potente UX, superficie sin profundidad técnica |
| **LangGraph** | 68/100 🟡 | Graph-based elegante pero dependencia cloud corrosiva |
| **AutoGen** | 52/100 🟠 | Buena idea, ejecución mediocre. Sin memoria ni privacidad real |
| **CORTEX** | **85/100** 🟢 | El stack más soberano y profundo del ecosistema |

### Desglose OpenClaw (71/100)

| Dimensión | Pts | Razón |
|---|---|---|
| Velocidad de adopción | 18/20 | 100k GitHub stars en 2 meses |
| Privacidad / Soberanía | 16/20 | Local-first, sin telemetría |
| Profundidad técnica | 11/20 | Routing vs Byzantine consensus de CORTEX |
| Observabilidad | 14/20 | Live Canvas bueno, sin X-Ray 13D |
| Ecosistema / extensibilidad | 12/20 | Plugin system prometedor, aún inmaduro |

---

## 🔬 OpenClaw — Deep Dive

### Historia
- **Nov 2025:** Lanzado como "Clawdbot" (referencia a Claude de Anthropic).
- **Ene 2026:** Renombrado a "OpenClaw" tras quejas de trademark.
- **Feb 2026:** El creador (Peter Steinberger) se une a OpenAI. Proyecto pasa a fundación OSS.

### Arquitectura

```
┌─────────────────────────────────────────┐
│              LIVE CANVAS UI             │  ← Visual workspace (React)
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│           ORCHESTRATOR CORE             │
│  • Plan generator (LLM)                 │
│  • Task queue (async)                   │
│  • Multi-agent router                   │
└──┬──────────┬──────────┬────────────────┘
   │          │          │
┌──▼──┐  ┌───▼───┐  ┌───▼──────────┐
│FS   │  │Shell  │  │ Messaging    │
│Agent│  │Agent  │  │ Bridge       │
│     │  │       │  │ (WA/TG/DC)   │
└──┬──┘  └───┬───┘  └───┬──────────┘
   │          │          │
┌──▼──────────▼──────────▼──────────────┐
│         PLUGIN REGISTRY               │
│  • SAP adapter                        │
│  • DB adapter                         │
│  • Custom tools (SDK)                 │
└────────────────────────────────────────┘
```

### Plugin Contract

```python
from openclaw.plugin import BasePlugin, PluginResult

class SAPPlugin(BasePlugin):
    name = "sap"
    description = "Query SAP OData entities"

    async def run(self, intent: str, params: dict) -> PluginResult:
        async with SAPClient(config) as client:
            data = await client.read_entity_set(
                params["entity_set"],
                filters=params.get("filter")
            )
        return PluginResult(success=True, data=data)
```

> ✅ `cortex/sap/client.py` encaja como plugin de OpenClaw sin cambios.

---

## 🚀 Gap Analysis — CORTEX

```
CORTEX actual:               85/100
CORTEX + mensajería TG/WA:   92/100
CORTEX + Live Canvas UI:     97/100
```

### Lo que CORTEX ya gana

- **Byzantine Swarm** > routing básico de todos los demás
- **Memoria episódica real** (SQLite + L2 vector) — ninguno lo hace nativo
- **MEJORAlo / X-Ray 13D** — único sistema de calidad de código integrado
- **Async-first** desde el diseño, no añadido a posteriori

### Los únicos gaps reales

1. **Mensajería** — OpenClaw tiene WA/Telegram/Discord. CORTEX no.
2. **Live Canvas UI** — Visual workspace para ver el estado del agente en tiempo real.

### Integración potencial CORTEX ↔ OpenClaw

```
OpenClaw  →  interfaz de usuario + mensajería + orquestación básica
   ↓
CORTEX    →  memoria episódica, swarm Byzantine, MEJORAlo, persistencia soberana
   ↓
MOSKV-1   →  skills, workflows, identidad
```

OpenClaw actuaría como **frontend/gateway** (recibe órdenes por Telegram, las enruta a CORTEX).

---

## ⚠️ Riesgo OpenClaw

- Creador se va a OpenAI → riesgo de pérdida de dirección del proyecto.
- Plugin system aún inmaduro en producción.
- Memory system superficial comparado con CORTEX.

---

*Análisis generado por MOSKV-1 · Actualizar al revisar nuevas versiones de OpenClaw.*
