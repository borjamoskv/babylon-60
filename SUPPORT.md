# Support

This document defines how to get help, what is currently supported, and what a commercial evaluator should assume by default.

## Channels

- **Security vulnerabilities:** email [security@cortexpersist.com](mailto:security@cortexpersist.com). Do not open public issues for vulnerabilities.
- **Bug reports and feature requests:** open a GitHub issue in this repository.
- **Private technical diligence or acquisition conversations:** contact [borja@moskv.com](mailto:borja@moskv.com).

## Current Support Posture

CORTEX Persist is maintained as an actively developed open-source project with a beta product line.

Unless separately agreed in writing, this repository does not imply a paid support contract, formal escalation ladder, or managed-service obligation.

| Release line | Status | Support expectation |
| :--- | :--- | :--- |
| `0.3.x` beta | Active | Best-effort bug fixes, security triage, and documentation updates |
| `< 0.3.0` | Unsupported | Upgrade required before support review |

## Response Targets

- **Security reports:** acknowledgment within 48 hours and severity triage within 5 business days
- **Public bug reports:** best effort, prioritized by severity and reproducibility
- **Documentation issues:** best effort, usually batched with the next maintenance pass

These are response targets, not contractual SLAs.

## What Support Covers

- Installation and packaging issues
- Reproducible bugs in documented features
- Security report intake and triage
- Clarification of intended behavior for public CLI and API surfaces

## What Support Does Not Automatically Cover

- Custom feature development
- On-call coverage
- Managed hosting or data operations
- Buyer-specific compliance sign-off
- Migration design for heavily customized forks
- Contractual SLAs or guaranteed escalation

## Guidance For Enterprise Evaluation

If you are evaluating CORTEX for regulated or high-stakes use, review these documents together:

- [README.md](README.md)
- [ENTERPRISE_READINESS.md](ENTERPRISE_READINESS.md)
- [DUE_DILIGENCE_CHECKLIST.md](DUE_DILIGENCE_CHECKLIST.md)
- [DEPLOYMENT_HARDENING.md](DEPLOYMENT_HARDENING.md)
- [SECURITY.md](SECURITY.md)
- [VERSION_SUPPORT.md](VERSION_SUPPORT.md)
- [RELEASE_PROCESS.md](RELEASE_PROCESS.md)
- [MAINTAINERS.md](MAINTAINERS.md)
- [https://cortexpersist.com/docs/security_trust_model](https://cortexpersist.com/docs/security_trust_model)
- [https://cortexpersist.com/docs/architecture](https://cortexpersist.com/docs/architecture)
- [https://cortexpersist.com/docs/operations](https://cortexpersist.com/docs/operations)

Align commercial expectations explicitly before treating this repository as a managed platform commitment.
