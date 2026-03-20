# experimental/

> Substrato del ciclo autónomo — módulos en incubación activa que implementan
> las fases de observación, acción, modulación y compactación del agente soberano.

**Estado global:** `INCUBATING` — excluido de ruff, pyright y pytest por defecto
(ver `pyproject.toml` → `[tool.ruff]` y `[tool.pyright]`).

---

## Arquitectura: el Ciclo Ω₃

Los módulos no son entidades aisladas. Son fases de un único ciclo autónomo:

```
┌─────────────────────────────────────────────────────────┐
│                   CICLO AUTÓNOMO Ω₃                     │
│                                                         │
│  OBSERVAR ──────► HIPOTETIZAR ──────► ACTUAR            │
│     │                                    │              │
│  ZeroPrompting              StrategicDisobedience       │
│  (detecta fricción)         (valida antes de actuar)    │
│     │                                    │              │
│  CircadianCycle ◄──── DigitalEndocrine ◄─┘              │
│  (scheduler)          (modula temperatura/estilo)       │
│     │                                                   │
│  SLEEP PHASE ──────► MEDIR ──────────► REPETIR          │
│     │                                    │              │
│  Autopoiesis                    EpigeneticMemory        │
│  (genera herramientas)          (acumula reward/pain)   │
└─────────────────────────────────────────────────────────┘
```

---

## Módulos

### `circadian_cycle.py` — Scheduler del ciclo

**Estado:** `INCUBATING`
**Integración core:** ❌ standalone
**Candidato a:** `cortex/extensions/daemon/` o `nightshift_daemon.py`

Implementa el day/night cycle: fase activa (procesa requests) vs fase sleep
(mantenimiento: pruning, compactación, síntesis de insights).

```python
from experimental.circadian_cycle import CircadianCycle
cc = CircadianCycle(wake_hour=7, sleep_hour=23)
cc.register_sleep_task(lambda: compaction_run())
```

**Dependencias core necesarias para promover:** scheduler externo (puede conectar
con `nightshift_daemon.py` que ya existe en `cortex/extensions/swarm/`).

---

### `zero_prompting.py` — Emisor proactivo

**Estado:** `INCUBATING`
**Integración core:** ❌ standalone
**Candidato a:** `cortex/extensions/swarm/` o `daemon/core.py`

Detecta fricción por idle time y emite sugerencias proactivas sin esperar prompt.
Implementa la *proactividad radical* — el agente actúa cuando detecta bloqueo.

```python
from experimental.zero_prompting import ZeroPrompting
zp = ZeroPrompting(idle_threshold_seconds=900, notify=push_notification)
zp.start_background_loop(interval=30)
```

**Bloqueante para promover:** necesita async (`asyncio.sleep` vs `time.sleep`).

---

### `digital_endocrine.py` — Modulador de hiperparámetros

**Estado:** `INCUBATING`
**Integración core:** ❌ standalone
**Candidato a:** `cortex/llm/` o `cortex/extensions/llm/router.py`

Sistema endocrino digital: modula `temperature` del LLM en función de señales
contextuales (urgencia → cortisol alto → temperatura baja; creatividad → dopamina alta → temperatura alta).

```python
from experimental.digital_endocrine import DigitalEndocrine
de = DigitalEndocrine()
de.ingest_context(user_message)
current_temp = de.temperature       # float [0.0, 1.0]
style = de.response_style           # "telegraphic" | "expansive" | "cautious" | "balanced"
```

**Bloqueante para promover:** integrar con `cortex/llm/router.py` — el router
necesita un hook para temperatura dinámica.

---

### `epigenetic_memory.py` — Memoria con peso emocional

**Estado:** `INCUBATING`
**Integración core:** ❌ standalone
**Candidato a:** `cortex/memory/` (capa sobre el vector store existente)

Vector store con `emotion_weight ∈ [-1.0, 1.0]`. Recuperación sesgada:
memorias de alto dolor → penalizadas (×0.1), memorias positivas → amplificadas (×2.0).

```python
from experimental.epigenetic_memory import EpigeneticMemory
mem = EpigeneticMemory()
mem.upsert(content, embedding, emotion_weight=-0.9)  # experiencia negativa
results = mem.retrieve(query_embedding, top_k=5)
```

**Bloqueante para promover:** reemplazar `_store` dict en-memoria por
`sqlite-vec` (ya disponible en el core). Integrar con `cortex/memory/`.

---

### `autopoiesis.py` — Motor de auto-creación de herramientas

**Estado:** `INCUBATING`
**Integración core:** ❌ standalone
**Candidato a:** `cortex/extensions/` (sandbox separado)

Genera scripts Python on-demand, los ejecuta en Docker sandbox y los registra
si superan validación. Implementa el concepto de *auto-creación*: el agente
escribe su propia tooling cuando detecta una capability gap.

```python
from experimental.autopoiesis import Autopoiesis
ap = Autopoiesis(tool_dir="./generated_tools")
path = ap.generate_and_register(generator=gen_fn, validator=val_fn)
```

**Bloqueante para promover:** requiere Docker en runtime. Riesgo de seguridad
alto — necesita guard de injection antes de ejecutar código generado por LLM.
Revisar con `SecurityWarden` antes de cualquier promoción.

---

### `strategic_disobedience.py` — Gate de fricción

**Estado:** `INCUBATING`
**Integración core:** ❌ standalone
**Candidato a:** `cortex/guards/` (como guard pre-ejecución)

Evalúa requests y los reta cuando detecta riesgo. Implementa el *Abogado del Diablo*:
anti-sycophancy estructural. Score heurístico de riesgo → `challenge` o `proceed`.

```python
from experimental.strategic_disobedience import StrategicDisobedience
sd = StrategicDisobedience()
result = sd.evaluate(request)
# {"action": "challenge", "risk_score": 0.7, "alternatives": [...]}
# {"action": "proceed", "risk_score": 0.2}
```

**Bloqueante para promover:** reemplazar heurística keyword-based por un
clasificador tipado. El threshold `0.6` necesita calibración con datos reales.

---

### `idc/` — Subdirectory

**Estado:** `UNKNOWN` — no auditado.
**Acción pendiente:** catalogar contenido y declarar estado.

---

### Tests en `experimental/`

| Fichero | Módulo target | Estado |
|:--------|:-------------|:-------|
| `test_aleph.py` | Desconocido (`aleph`) | `ORPHAN` — módulo no existe |
| `test_bio.py` | Bio-layer | `ORPHAN` — módulo no existe |
| `test_bridge.py` (164B) | `bridge` | `SKELETON` — sin assertions |
| `test_centaur_heartbeat.py` | Centaur | `ORPHAN` — módulo no existe |
| `test_centauro.py` (267B) | Centaur | `SKELETON` |
| `test_db_init.py` | DB init | `INTEGRACIÓN PARCIAL` |
| `test_hologram.py` | Hologram | `ORPHAN` |
| `test_physical.py` | Physical layer | `ORPHAN` |
| `test_semantic_dedup.py` | Semantic dedup | `INTEGRACIÓN PARCIAL` |

Tests `ORPHAN` y `SKELETON` → candidatos a purga en el próximo ciclo de compactación.

---

## Política de promoción

Un módulo sale de `experimental/` cuando cumple **todos**:

- [ ] Tests unitarios con `pytest` (≥80% coverage del módulo)
- [ ] Type hints completos en la API pública
- [ ] Sin `time.sleep()` en paths async
- [ ] Guard de seguridad si ejecuta código externo o LLM output
- [ ] Integración demostrable con un módulo de `cortex/`
- [ ] Revisión en PR con reviewer humano

Un módulo se purga cuando lleva **>90 días** sin commits y ningún módulo core lo referencia.
