# CORTEX Persist

Tamper-evident memory and decision lineage for AI agents.

CORTEX Persist is a local-first trust layer for facts, decisions, errors, and state transitions. It gives you hash-chained records, verification commands, and audit-ready exports so you can prove what an agent knew and when it knew it.

[Quickstart](docs/quickstart.md) · [Installation](docs/installation.md) · [CLI](docs/cli.md) · [API](docs/api.md) · [Security](docs/SECURITY_TRUST_MODEL.md) · [Roadmap](ROADMAP.md) · [Contributing](CONTRIBUTING.md)

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/borjamoskv/Cortex-Persist/actions/workflows/ci.yml/badge.svg)](https://github.com/borjamoskv/Cortex-Persist/actions)
[![Codecov](https://codecov.io/gh/borjamoskv/Cortex-Persist/branch/main/graph/badge.svg)](https://codecov.io/gh/borjamoskv/Cortex-Persist)
[![PyPI](https://img.shields.io/pypi/v/cortex-persist.svg)](https://pypi.org/project/cortex-persist/)

---

## What It Is

CORTEX Persist is designed for teams shipping AI into workflows where a plain log is not enough.

- Store structured facts and decisions.
- Hash-chain every write into a tamper-evident ledger.
- Verify the ledger when you need evidence, not guesses.
- Export artifacts for reviews, audits, and incident response.

It sits alongside your existing stack. Use it with your current database, observability tools, and vector search where that makes sense.

## Best Fit

- Agent workflows that can take irreversible actions.
- Support, approval, pricing, finance, and compliance flows.
- Long-running systems that need traceable state transitions.
- Teams that need a defensible record after the fact.

## Not a Replacement For

- Observability platforms such as Datadog or ELK.
- Dedicated vector databases for ephemeral retrieval.
- Human review, legal review, or compliance judgment.

## Install

### From PyPI

```bash
pip install cortex-persist
```

Then verify the install:

```bash
cortex --version
cortex init
cortex status
```

### From Source

```bash
git clone https://github.com/borjamoskv/Cortex-Persist.git
cd Cortex-Persist
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

For the API server and MCP surface:

```bash
pip install cortex-persist[api]
```

## Quickstart

```bash
# Initialize the local ledger
cortex init

# Store a fact
cortex store my-project "Redis uses skip lists for sorted sets" --tags "redis,data-structures"

# Store a decision
cortex store my-project "We chose FastAPI over Flask for async support" --type decision

# Verify integrity
cortex verify 1
cortex ledger verify

# Generate a compliance snapshot
cortex compliance-report
```

If you want the full walkthrough, see [docs/quickstart.md](docs/quickstart.md).

## Local Model Automation (optional)

The scripts package includes local helpers to choose a model and dispatch tasks by workflow:

```bash
npm run model:pick -- "Texto de tarea"
npm run model:guide -- --json
npm run model:dispatch -- --json "Necesito compilar y validar el site" -- "npm run build"
npm run task:build -- --json "Compilar y validar la web"
npm run task:auto -- --json "Necesito compilar, testear y cerrar validación de la web antes del deploy"
npm run test:models
```

It supports `build|web|test|ship|release`, environment-based flow selection, and `--dry-run` for safe planning.

See [scripts/README.md](scripts/README.md) for full details.

## Python Integration

```python
import asyncio
from cortex import CortexEngine


async def main() -> None:
    engine = CortexEngine()

    fact_id = await engine.store(
        project="demo-agent",
        content="User approved transaction $5,000",
        fact_type="decision",
    )

    results = await engine.search("transaction approval", top_k=3, project="demo-agent")
    ledger = await engine.verify_ledger()

    assert fact_id
    assert results
    assert ledger.get("valid") is True


asyncio.run(main())
```

See [docs/api.md](docs/api.md) for the HTTP surface and [examples/demo_canonical.py](examples/demo_canonical.py) for a longer end-to-end demo.

## Repository Layout

- `cortex/` - Python engine, CLI, memory, verification, and core runtime.
- `api/` - FastAPI application and HTTP endpoints.
- `sdks/python/` and `sdks/js/` - experimental hosted API clients.
- `src/` - Astro landing pages and site UI.
- `docs/` - installation, architecture, security, and operational docs.
- `examples/` - runnable demos and integration examples.

## Documentation

- [Quickstart](docs/quickstart.md)
- [Installation](docs/installation.md)
- [CLI Reference](docs/cli.md)
- [API Reference](docs/api.md)
- [Security & Trust Model](docs/SECURITY_TRUST_MODEL.md)
- [Canonical Naming](docs/NAMING.md)
- [Architecture](docs/architecture/overview.md)

## License

Apache License 2.0. See [LICENSE](LICENSE).

*Built by [borjamoskv.com](https://borjamoskv.com) and [cortexpersist.com](https://cortexpersist.com)*
