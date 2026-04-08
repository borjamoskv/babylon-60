# Release Process

This document describes the public release flow for CORTEX Persist.

## Release Model

CORTEX Persist uses tagged releases for package publication.

- version metadata lives in [pyproject.toml](pyproject.toml)
- release tags follow the `v*` pattern
- PyPI publishing is handled by GitHub Actions

## Release Workflow

The authoritative workflow is:

- [.github/workflows/release.yml](.github/workflows/release.yml)

At a high level, the workflow:

1. checks out the repository
2. builds source and wheel artifacts
3. generates build provenance
4. publishes to PyPI
5. signs artifacts with Sigstore
6. uploads signed artifacts for traceability

## Pre-Release Expectations

Before cutting a release:

- ensure CI is green
- confirm package metadata is accurate
- confirm user-facing documentation matches shipped behavior
- confirm any security-sensitive release notes are coordinated privately when needed
- confirm the target release line matches the support posture in [VERSION_SUPPORT.md](VERSION_SUPPORT.md)

## Release Authority

This repository currently follows a maintainer-led release model. Release publication authority is effectively held by the primary maintainer until a broader maintainer structure is documented.

## Rollback And Revocation

If a bad package or release is published:

- stop further promotion of that version
- publish a corrective release rather than silently replacing artifacts
- document the affected release line in public release notes when appropriate
- treat old unsupported lines as forward-fix only unless an exception is stated explicitly

## Supply-Chain Signals

Public supply-chain posture is supported by:

- signed release artifacts
- GitHub Actions provenance
- dependency audit in CI
- SBOM generation
- container image scanning

See [SECURITY.md](SECURITY.md) for the public-facing security summary.
