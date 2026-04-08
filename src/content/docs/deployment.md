---
title: "Deployment"
description: "CORTEX Persist Documentation — Deployment"
---


CORTEX Persist is currently easiest to deploy in local-first or operator-managed self-hosted environments. This page intentionally documents the paths that are present in the repository today, rather than aspirational platform layers.

---

## Current Deployment Posture

The most practical deployment paths today are:

- direct Python package install
- the included Dockerfile
- a self-hosted reverse proxy and backup strategy managed by the operator

What is not bundled here as first-class release artifacts:

- a production `docker-compose` stack
- a Helm chart
- a managed cloud control plane

For a buyer-facing deployment checklist, see [DEPLOYMENT_HARDENING.md](../../../DEPLOYMENT_HARDENING.md).

---

## Local API

```bash
pip install cortex-persist[api]
cortex init
uvicorn cortex.api:app --host 0.0.0.0 --port 8484
```

Default local database path:

```text
~/.cortex/cortex.db
```

To override it:

```bash
export CORTEX_DB_PATH=/absolute/path/to/cortex.db
```

---

## Docker

Build from the included Dockerfile:

```bash
docker build -t cortex:latest .
```

Run a local container:

```bash
docker run --rm -d \
  --name cortex \
  -p 8484:8484 \
  -e CORTEX_DB_PATH=/data/cortex.db \
  -v cortex-data:/data \
  cortex:latest
```

For a more production-like operator-managed run:

```bash
docker run --rm -d \
  --name cortex \
  -p 8484:8484 \
  -e CORTEX_DEPLOY=cloud \
  -e CORTEX_DB_PATH=/data/cortex.db \
  -e CORTEX_ALLOWED_ORIGINS=https://your-ui.example.com \
  -e CORTEX_MASTER_KEY=BASE64_32_BYTE_AES_KEY \
  -v cortex-data:/data \
  cortex:latest
```

Then verify the container is healthy:

```bash
curl -f http://127.0.0.1:8484/health
```

---

## Daemon

The repository ships a separate daemon entrypoint:

```bash
moskv-daemon --help
```

Common commands:

```bash
moskv-daemon check
moskv-daemon status
moskv-daemon install
moskv-daemon uninstall
```

Use `moskv-daemon`, not `cortex daemon`.

---

## Environment Variables In Active Use

The following are documented and reflected in the current config layer:

| Variable | Purpose |
| :--- | :--- |
| `CORTEX_DB_PATH` | Primary database-path override |
| `CORTEX_DB` | Legacy database-path override |
| `CORTEX_ALLOWED_ORIGINS` | CORS allowlist |
| `CORTEX_RATE_LIMIT` | Request budget per window |
| `CORTEX_RATE_WINDOW` | Rate-limit window |
| `CORTEX_DEPLOY` | Deployment mode; `cloud` disables interactive docs |
| `CORTEX_MASTER_KEY` | Base64 AES key fallback when OS keyring is unavailable |
| `CORTEX_VAULT_KEY` | Alternate key fallback |

See [.env.example](../../../.env.example) for the current env template shipped in the repository.

---

## Operational Expectations

- keep the service behind TLS
- pin exact versions
- back up the database and encryption key material together
- run periodic ledger verification
- validate rollback before calling a deployment production-ready

---

## Related Documents

- [Operations](OPERATIONS.md)
- [API](api.md)
- [Deployment Hardening](../../../DEPLOYMENT_HARDENING.md)
- [Due Diligence Checklist](../../../DUE_DILIGENCE_CHECKLIST.md)
