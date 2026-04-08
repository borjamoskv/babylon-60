# Security Policy

## Supported Versions

| Release line | Status | Notes |
| :--- | :---: | :--- |
| `0.3.x` beta | ✅ Active | Security triage and critical fixes are handled on a best-effort basis |
| `< 0.3.0` | ❌ Unsupported | Upgrade required before support review |

## Reporting a Vulnerability

**Do NOT open a public issue for security vulnerabilities.**

Email: **<security@cortexpersist.com>**

You will receive an acknowledgment within 48 hours and a detailed response within 5 business days.

## Security Response Targets

- Acknowledge new reports within 48 hours
- Triage reported severity within 5 business days
- Coordinate disclosure privately until a fix or mitigation is available

These are response targets, not contractual SLAs.

## Security Features

CORTEX is built security-first:

- **SHA-256 hash-chained ledger** — tamper-evident fact storage
- **Merkle tree checkpoints** — batch integrity verification
- **Privacy Shield** — 11-pattern secret detection at ingress
- **AST Sandbox** — safe LLM code execution without `eval()`
- **RBAC** — 4-role access control (`SYSTEM`, `ADMIN`, `AGENT`, `VIEWER`)
- **Security Headers Middleware** — CSP, HSTS, X-Frame-Options
- **Input Sanitization** — all user inputs validated and escaped

## Supply Chain Security

### Release Signing

All CORTEX releases published to PyPI are **cryptographically signed using [Sigstore](https://sigstore.dev/)**. This provides:

- **Provenance verification** — Confirm artifacts were built by our CI pipeline
- **Tamper detection** — Verify packages haven't been modified after signing
- **Keyless signing** — Uses OIDC identity, no long-lived keys to compromise

To verify a release:

```bash
pip install sigstore
sigstore verify identity \
  --cert-oidc-issuer https://token.actions.githubusercontent.com \
  --cert-identity https://github.com/borjamoskv/Cortex-Persist/.github/workflows/release.yml@refs/tags/v0.3.0 \
  cortex_persist-0.3.0.tar.gz
```

### Container Image Scanning

Every CI pipeline run scans the Docker image with **[Trivy](https://trivy.dev/)** for:

- Known CVEs in OS packages and Python dependencies
- **CRITICAL** and **HIGH** severity findings block the build
- Scan results are visible in GitHub Actions logs

### Dependency Auditing

CI runs **[pip-audit](https://github.com/pypa/pip-audit)** on every push to detect known vulnerabilities in Python dependencies. Any finding fails the build.

## Threat Model

CORTEX assumes:

- The local SQLite database is as secure as the host filesystem
- Network APIs require authentication (API keys or JWT)
- Multi-tenant deployments enforce strict tenant isolation via `tenant_id` scoping
- **Untrusted plugins** execute in containerized sandboxes with no host network access
- **Supply chain attacks** are mitigated by Sigstore signing + pip-audit + Trivy

## Shared Responsibility Note

Repository-level security controls do not eliminate operator responsibility. Real deployments still need correct TLS termination, reverse proxying, network exposure control, CORS restriction, backup handling, and secret rotation.

Encrypted persisted data also depends on key continuity. In environments without stable OS keyring access, operators need stable `CORTEX_MASTER_KEY` or `CORTEX_VAULT_KEY` management; otherwise encrypted facts may become unreadable after redeploy or restore.

For deployment-side controls, see [DEPLOYMENT_HARDENING.md](./DEPLOYMENT_HARDENING.md).

### Attack Vectors & Mitigations

| Vector | Mitigation |
| :--- | :--- |
| Tampered package on PyPI | Sigstore signature verification |
| Vulnerable dependency | pip-audit in CI, Dependabot alerts |
| Compromised container image | Trivy scan (CRITICAL/HIGH block) |
| Memory tampering | SHA-256 hash chain + Merkle checkpoints |
| Unauthorized access | RBAC + API key + JWT authentication |
| Secret leakage | Privacy Shield (11 regex patterns at ingress) |
| **Composition leakage** | **Holistic cross-field correlation analysis at ingress** |
| Malicious LLM code output | AST Sandbox (no eval/exec) |
| Cross-tenant data access | Tenant ID scoping on all queries |

> **⚠️ Composition Leakage:** Two individually innocuous data points that, when combined by an adversary, reconstruct a secret (e.g., deploy address + contract salt = proxy key). This is the differential privacy analog of correlation attacks. CORTEX's Privacy Shield evaluates facts holistically — not per-field — scoring each new fact against the combinatorial surface of related stored data.

---

## Related Security Documentation

For trust boundaries, verification flow, ledger continuity, and cognitive/state-mutation
security surfaces, see
[`docs/SECURITY_TRUST_MODEL.md`](./docs/SECURITY_TRUST_MODEL.md).
