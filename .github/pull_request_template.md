## Summary

<!-- Briefly explain the change and why it exists. -->

## Change Type

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Security fix
- [ ] Refactor / maintenance

## Affected Surfaces

- [ ] `cortex/engine`
- [ ] `cortex/memory`
- [ ] `cortex/guards`
- [ ] `cortex/ledger`
- [ ] `cortex/routes` or public API contract
- [ ] CLI surface
- [ ] Migrations / schema
- [ ] Docs only

## Validation

- [ ] Tests pass
- [ ] Ruff passes
- [ ] Pyright passes
- [ ] No hardcoded secrets or API keys
- [ ] Documentation updated where needed
- [ ] CHANGELOG updated if user-facing

## Trust And Ops Checklist

- [ ] Tenant isolation behavior preserved
- [ ] No validation downgrade or guard bypass introduced
- [ ] No blocking calls added to async paths
- [ ] Migration review completed and rollback impact understood
- [ ] Ledger / audit implications reviewed for trust-surface changes

## Rollback Plan

<!-- Explain how to back out this change safely if it causes regressions. -->

## Follow-ups

<!-- List known follow-up work, if any. -->
