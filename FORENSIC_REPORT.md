# 🕵️ DETECTIVE-Ω — Forensic Analysis Report
**Target**: `CORTEX-Persist` (Engine) & `EXERGIA-Ω` (Visual Substrate)
**Timestamp**: 2026-05-27
**Reality Level**: C5-REAL

## 1. Heatmap (8 Dimensions)

| # | Vector | Status | Criticality / Findings |
|---|---|---|---|
| 1 | **God Objects** | 🔴 | `cortex/engine/__init__.py` (621 LOC). Utiliza 11 Mixins (`SearchMixin`, `StoreMixin`, etc.) para mitigar el peso, pero sigue siendo un Facade masivo (God Object arquitectónico) que concentra el ciclo de vida (init, teardown, pool). `harmony-forge/index.html` (508 LOC) requiere componentización estructural. |
| 2 | **Circulars** | 🟢 | Limpio. Las dependencias `TYPE_CHECKING` previenen ciclos de importación entre `CortexEngine` y los managers (`FactManager`, `ConsensusManager`). |
| 3 | **Dead Code** | 🟡 | Se detectó `tests/test_llamaindex_bridge.py` y `test_swarm_budget.py` que fueron asimilados recientemente. Existen vestigios de la transición sincrónica en los mixins que podrían considerarse código muerto en entornos puramente asíncronos. |
| 4 | **Copy-Paste** | 🟢 | Código DRy-ed adecuadamente vía `CortexEngine` Mixins. No se detectan duplicidades > 10 líneas en el Core. |
| 5 | **Security** | 🟢 | Hardening reciente vía `zk_hardware.py` (ChaCha20-Poly1305) y `pipeline.py` blindan vectores de filtración. Cero hardcoded secrets en `docker-compose.yml`. |
| 6 | **Error Handling** | 🟡 | Detectados bloques `except Exception as e:` amplios en la propagación de Gossip y teardown (`SyncMixin`). Requiere tipado de excepciones más estricto. |
| 7 | **Naming** | 🟢 | Alineado al estándar `MOSKV`. Los Daemons (ej: `OuroborosEngine`) y métodos (`health_check`) tienen nombres semánticamente precisos. |
| 8 | **Perf** | 🟠 | Posible cuello de botella (Contención de SQLite WAL) mitigado con Thread-local concurrency, pero `cortex/extensions/langchain_bridge.py` y la serialización FTS5 deben monitorizarse bajo cargas LEGION-10k. |

## 2. Sprint 1: Quick Wins (Inmediato)
- Refactorizar `harmony-forge/index.html` separando el CSS/JS inline en assets modulares (`.css`, `.js`).
- Purgar el manejador `except Exception as e:` en `gossip.py` para capturar explícitamente `ConnectionError` o `TimeoutError`.

## 3. Sprint 2: Medium Refactors
- Extraer el bloque de inicialización de la base de datos (Pool / SQLite-vec loading) fuera del `__init__.py` hacia una factoría estricta (`CortexEngineFactory`).

## 4. Sprint 3: Deep Logic Overhaul
- Mapeo completo a la infraestructura AlloyDB/PostgreSQL. Retirar paulatinamente `SyncMixin` a medida que la arquitectura adopte 100% AsyncPG + Federated Shards.
