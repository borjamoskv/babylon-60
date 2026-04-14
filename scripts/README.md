# scripts/

> Operational scripts for CORTEX — benchmarks, seeders, gates, daemons, and utilities.

## Categories

| Category | Scripts | Purpose |
|---|---|---|
| **Benchmark** | `benchmark.py`, `benchmark_maas.py`, `benchmark_viz.py` | Performance measurement |
| **Pre-commit** | `entropy_gate.py`, `sovereign_pre_commit.py`, `neural_pre_commit.py`, `sovereign_pre_commit.sh`, `zero_debt.sh` | Code quality gates |
| **Ship Gate** | `ship_gate.py` | Release readiness checks |
| **Daemons** | `academy_trainer_daemon.py`, `void_watcher_daemon.py`, `storm_watcher_l2.py`, `moskv_panopticon.py`, `panopticon_live.py` | Background processes |
| **Seeders** | `seed_*.py`, `backfill_embeddings.py` | Data population |
| **DB Maintenance** | `repair_db.py`, `encrypt_legacy_facts.py`, `repatriate_memories.py` | Database operations |
| **Forge** | `forge_*.py` | Build & generation pipelines |
| **Verify** | `repo_health_changed.py`, `verify_*.py` | Architecture verification and changed-file triage |
| **Orchestrators** | `god_mode_orchestrator.py`, `mejoralo_infinito.py`, `orchestrator.py`, `rotate_aether.py` | Meta-execution |
| **Agent Demo** | `run_github_agent_demo.py` | End-to-end harness for the `GitHubAgent` builtin |
| **MCP / API** | `run_mcp_server.py`, `smoke_test_api.py` | Server launching |
| **NotebookLM** | `fragment_notebooklm.py`, `synthesize_notebooklm.py` | NotebookLM integration |
| **Shell** | `cortex-boot.sh`, `cortex_persist.sh`, `diagnose.sh`, etc. | System operations |

## Safety Guards

Scripts with destructive operations require explicit opt-in:

| Script | Guard |
|---|---|
| `repatriate_memories.py` | `--force` flag or interactive `YES` confirmation |
| `infinite_ouroboros.sh` | `CORTEX_ALLOW_INFINITE=1` env var + `MAX_CYCLES` (default 50) |
| `infinite_investigation.sh` | `CORTEX_ALLOW_INFINITE=1` env var + `MAX_CYCLES` (default 50) |

## `_archive/`

Contains superseded, one-shot, and experimental scripts preserved for archaeological reference. Safe to delete entirely.

## Automatización de modelos (motor local)

```bash
npm run model:pick -- "Texto de tarea"
npm run model:guide
npm run model:guide -- --json
npm run model:dispatch -- "Texto de tarea" -- "npm run build"

# Modo orquestado (sin pasar --):
TASK_COMMAND="npm run build" npm run model:dispatch -- "Necesito compilar y validar el site"

# Modo orquestado automático por flujo:
TASK_FLOW=build TASK_COMMAND="npm run build" npm run model:dispatch -- --auto "Necesito compilar y validar el site"

# Modo orquestado desde entorno (opcional):
TASK_FLOW=web TASK_COMMAND="npm run build" npm run task:run -- "Revisa el sitio y aplica el flujo web"

# Modo simulación (sin ejecutar):
TASK_FLOW=release TASK_COMMAND="npm run build" npm run model:dispatch -- --dry-run --auto "Simula preparación de release"
```

## Guía rápida: qué modelo usar

| Modelo | Mejor para |
|---|---|
| `gpt-5.4` | Arquitectura, producto y decisiones complejas |
| `gpt-5.4-Mini` | Explicación técnica rápida y consultas de ayuda |
| `gpt-5.3-codex` | Bugfixes, refactors, integración y despliegue |
| `gpt-5.3-codex-spark` | Ajustes de UI, texto, estilos o cambios puntuales |
| `gpt-5.2` | Planes, coordinación y sesiones de trabajo prolongadas |

## Scripts npm listos para flujo

```bash
npm run task:build -- "Compilar y validar la web"
npm run task:web -- --json "Genera recomendaciones de modelado para este texto"
npm run task:test -- "Verificar estado rápido antes de merge"
npm run task:release -- "Preparar salida de release"
npm run task:ship -- "Preparar artefacto y cerrar ciclo"
npm run task:auto -- --json "Necesito compilar, testear y revisar la web antes de deploy"
```

Cuando `TASK_COMMAND` (o `CODEX_TASK_COMMAND` / `MODEL_ROUTER_COMMAND`) está presente, el dispatcher resuelve el modelo
y ejecuta ese comando inyectando `CODEX_MODEL`, `MODEL_DISPATCH` y `MODEL_ROUTER_SELECTION` en el entorno.
Con `--dry-run`, el dispatcher no ejecuta el comando y devuelve el plan resuelto en JSON/plain.

Si defines `TASK_FLOW`, no necesitas pasar `--flow` explícitamente; al mismo tiempo puedes forzarlo con:
`--auto --flow=<build|release|ship|web|test>`.

Para validar regresiones del motor:

```bash
npm run test:models
```
