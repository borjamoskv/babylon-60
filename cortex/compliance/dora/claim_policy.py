"""Claim-policy scanner for regulated evidence wording."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


FORBIDDEN_CLAIMS: tuple[str, ...] = (
    "DORA compliant",
    "DORA certified",
    "EU AI Act compliant by default",
    "full EU AI Act compliance",
    "legal compliance guaranteed",
    "compliance by default",
    "bank-production ready",
    "production-readiness certification",
    "tamper-proof",
    "unhackable",
    "guaranteed compliance",
    "fully secure",
    "zero risk",
)

CONDITIONAL_CLAIMS: tuple[str, ...] = (
    "EU-only",
    "no subprocessors",
    "audit-ready",
)

ALLOW_MARKER = "claim-policy: allow"


@dataclass(frozen=True)
class ClaimFinding:
    """A claim-policy match in text or a file."""

    term: str
    line: int
    text: str
    path: Path | None = None
    conditional: bool = False


def scan_text_for_claims(
    text: str,
    *,
    include_conditional: bool = True,
    path: Path | None = None,
) -> list[ClaimFinding]:
    """Scan text for prohibited or conditional DORA claim terms."""

    terms = list(FORBIDDEN_CLAIMS)
    if include_conditional:
        terms.extend(CONDITIONAL_CLAIMS)

    findings: list[ClaimFinding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        line_lower = line.lower()
        if ALLOW_MARKER in line_lower:
            continue
        for term in terms:
            if term.lower() not in line_lower:
                continue
            findings.append(
                ClaimFinding(
                    term=term,
                    line=line_number,
                    text=line.strip(),
                    path=path,
                    conditional=term in CONDITIONAL_CLAIMS,
                )
            )
    return findings


def scan_file_for_claims(path: str | Path, *, include_conditional: bool = True) -> list[ClaimFinding]:
    """Scan a UTF-8 file for DORA claim-policy terms."""

    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    return scan_text_for_claims(text, include_conditional=include_conditional, path=file_path)
