---
title: "REST API Reference"
description: "CORTEX Persist Documentation — REST API Reference"
---


CORTEX exposes a FastAPI application via `cortex.api:app`. The public HTTP surface is versioned
primarily under `/v1`, and interactive docs are available at `/docs` when the app is not running
in production mode.

---

## Run Locally

```bash
pip install cortex-persist[api]
uvicorn cortex.api:app --host 0.0.0.0 --port 8484
```

Interactive docs: `http://localhost:8484/docs`

To export a static OpenAPI document:

```bash
python -c "from cortex.api.openapi import export_openapi_spec; print(export_openapi_spec())"
```

By default this writes `docs/openapi.json`.

---

## Authentication

API keys are created through the admin surface and then passed as Bearer tokens.

```bash
# Bootstrap the first key on a fresh local instance
curl -X POST "http://localhost:8484/v1/admin/keys?name=my-client&tenant_id=default"

# Use the returned token on subsequent requests
curl -H "Authorization: Bearer ctx_xxxxxxxxxx" \
  http://localhost:8484/v1/status
```

On a fresh deployment, the first key can be self-provisioned without authentication. Once a key
exists, creating additional keys requires an admin Bearer token.

### RBAC Roles

| Role | Permissions |
| :--- | :--- |
| `SYSTEM` | Full access |
| `ADMIN` | Administrative and write operations |
| `AGENT` | Read and write operations |
| `VIEWER` | Read-only access |

---

## Core Endpoints

### Facts & Memory

- `POST /v1/facts` — Store a single fact for the authenticated tenant.
- `POST /v1/facts/batch` — Store up to 100 facts in one request.
- `GET /v1/facts` — List active facts across projects for the tenant. Supports `limit` and `offset`.
- `GET /v1/facts/{fact_id}` — Retrieve one fact with metadata and hash.
- `GET /v1/projects/{project}/facts` — Recall facts for a specific project. Supports `limit` and `offset`.
- `POST /v1/search` and `GET /v1/search` — Canonical search endpoints with optional `project`, `as_of`, tags, and Graph-RAG context.
- `GET /v1/facts/{fact_id}/history` — Retrieve the fact version/history chain.
- `GET /v1/facts/{fact_id}/chain` — Retrieve the causal chain for a fact.
- `GET /v1/facts/verify` — Verify ledger integrity across persisted facts.
- `POST /v1/facts/{fact_id}/vote` — Cast a consensus vote on a fact.
- `POST /v1/facts/{fact_id}/vote-v2` — Cast a reputation-weighted consensus vote.
- `GET /v1/facts/{fact_id}/votes` — List votes registered for a fact.
- `POST /v1/facts/{fact_id}/taint` — Trigger taint propagation from a suspect fact.
- `DELETE /v1/facts/{fact_id}` — Soft-deprecate a fact.

### Health, Admin & Runtime

- `GET /health` — Lightweight service health endpoint.
- `GET /v1/status` — Engine status, counts, and database size.
- `GET /v1/health/deep` — Deep subsystem health probes.
- `GET /v1/health/check` — Lightweight scored health summary.
- `GET /v1/health/score` — Numeric health score and grade.
- `GET /v1/health/report` — Full health report with warnings and recommendations.
- `GET /v1/health/metrics` — Raw metric snapshots for dashboards.
- `GET /v1/health/prometheus` — Prometheus exposition format.
- `GET /v1/health/history` — Persisted health score history.
- `POST /v1/admin/keys` — Create API keys.
- `GET /v1/admin/keys` — List API keys.
- `GET /v1/projects/{project}/export` — Export project facts as JSON.
- `GET /v1/daemon/status` — Read the daemon status snapshot.
- `GET /v1/runtime/health` — Runtime health for the active process.
- `GET /v1/runtime/boot_recovery` — Boot-recovery report for the current runtime.
- `GET /v1/llm/status` — LLM/provider status surface.

### Swarm & Orchestration

- `GET /v1/events/stream` — Server-sent event stream for live updates.
- `GET /v1/swarm/status` — Aggregate swarm health and active worktrees.
- `POST /v1/swarm/worktrees` — Provision an isolated git worktree.
- `GET /v1/swarm/worktrees/{worktree_id}` — Inspect a provisioned worktree.
- `DELETE /v1/swarm/worktrees/{worktree_id}` — Tear down a worktree.
- `POST /v1/swarm/psychohistory` — Run a psychohistory simulation.
- `POST /v1/ask` and `POST /v1/ask/stream` — Retrieval + synthesis endpoints.
- `GET /v1/context/*` — Context inference, signals, and history endpoints.

---

## Compatibility Notes

Legacy clients using `/v1/memories/*` are redirected to `/v1/facts/*` for backward
compatibility.

`POST /v1/facts/search` still works as a hidden compatibility alias, but new integrations should
prefer `/v1/search`.

Some route modules exist in the repository but are not mounted in the current FastAPI app build.
If an endpoint is not present in `app.routes` or `/docs`, treat it as non-public until exposed.
