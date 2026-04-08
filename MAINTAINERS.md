# Maintainers

This document describes who currently stewards CORTEX Persist and what that stewardship means in practice.

## Current Maintainer Model

CORTEX Persist currently operates under a primary-maintainer model.

| Scope | Primary steward |
| :--- | :--- |
| Repository stewardship | `@borjamoskv` |
| Security contact | `security@cortexpersist.com` |
| Technical diligence / commercial contact | `borja@moskv.com` |

## What The Maintainer Owns

- Release decisions and package publishing
- Review and merge decisions for trust-critical surfaces
- Security report intake and coordination
- Public roadmap curation
- Documentation quality for buyer-facing repository surfaces

## What Contributors Should Assume

- CODEOWNERS defines the authoritative review-owner mapping for protected surfaces
- Not every contribution will be accepted on roadmap fit alone
- Trust, ledger, migration, and tenant-isolation changes may require narrower review and slower acceptance
- Support targets are documented in [SUPPORT.md](SUPPORT.md), not implied by issue activity

## Concentration Risk

Large evaluators should note that the project currently has maintainer concentration risk. This does not invalidate the technology, but it is relevant to procurement, acquisition, and continuity planning.

The current mitigation is transparency:

- ownership is explicit
- release and support policies are documented
- governance expectations are written down
- critical repository surfaces are protected through CODEOWNERS and process

## Related Documents

- [REPO_GOVERNANCE.md](REPO_GOVERNANCE.md)
- [SUPPORT.md](SUPPORT.md)
- [VERSION_SUPPORT.md](VERSION_SUPPORT.md)
- [.github/CODEOWNERS](.github/CODEOWNERS)
