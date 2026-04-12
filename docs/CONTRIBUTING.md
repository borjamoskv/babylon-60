# CORTEX Persist Contribution Workflow

This page is the versioned summary for contributors working directly from GitHub. Pair it with the deeper local workflow in [root CONTRIBUTING.md on GitHub](https://github.com/borjamoskv/Cortex-Persist/blob/main/CONTRIBUTING.md).

## Bootstrap

```bash
git clone https://github.com/borjamoskv/Cortex-Persist.git
cd Cortex-Persist
pip install -e ".[dev]"
```

Install extra surfaces only when the task needs them:

```bash
pip install -e ".[api]"
pip install -e ".[cloud]"
pip install -e ".[all]"
```

## Required Reading For Critical Surfaces

- [AGENTS.md on GitHub](https://github.com/borjamoskv/Cortex-Persist/blob/main/AGENTS.md) for trust invariants and write-path rules
- [Security & Trust Model](SECURITY_TRUST_MODEL.md) for guarantees and non-guarantees
- [Architecture](architecture.md) for system boundaries and critical paths

## Minimum Quality Gates

Run these before opening a pull request:

```bash
pytest tests/ -v --cov=cortex
ruff check cortex/
pyright cortex/
```

If the change touches CLI, API, packaging, or docs, verify the corresponding public surface explicitly.

## Contribution Rules

- Keep CLI modules thin and move business logic into engine, services, or managers.
- Add tests for any changed behavior.
- Preserve tenant-aware behavior and trust-path validation.
- Update docs whenever public behavior or onboarding changes.
- Catch specific exceptions rather than broad fallbacks.

## Release-Adjacent Changes

If you touch packaging or release flow, also validate:

- [pyproject.toml on GitHub](https://github.com/borjamoskv/Cortex-Persist/blob/main/pyproject.toml)
- [scripts/release_preflight.py on GitHub](https://github.com/borjamoskv/Cortex-Persist/blob/main/scripts/release_preflight.py)
- [.github/workflows/release.yml on GitHub](https://github.com/borjamoskv/Cortex-Persist/blob/main/.github/workflows/release.yml)

## Related References

- [Root CONTRIBUTING.md on GitHub](https://github.com/borjamoskv/Cortex-Persist/blob/main/CONTRIBUTING.md)
- [SECURITY.md on GitHub](https://github.com/borjamoskv/Cortex-Persist/blob/main/SECURITY.md)
- [SUPPORT.md on GitHub](https://github.com/borjamoskv/Cortex-Persist/blob/main/SUPPORT.md)
- [API Reference](api.md)
