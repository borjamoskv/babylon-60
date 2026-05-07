"""SQL guardrails for low-level database adapters."""

from __future__ import annotations

import re
from typing import Final

__all__ = [
    "PROTECTED_FACT_TABLES",
    "is_protected_fact_table_dml",
    "reject_protected_fact_table_dml",
]

PROTECTED_FACT_TABLES: Final = frozenset(
    {
        "facts",
        "facts_fts",
        "fact_tags",
        "causal_edges",
    }
)

_PROTECTED_TABLE_PATTERN = "|".join(
    re.escape(table) for table in sorted(PROTECTED_FACT_TABLES, key=len, reverse=True)
)
_QUOTED_PROTECTED_TABLE_PATTERN = (
    rf"(?:{_PROTECTED_TABLE_PATTERN})|"
    rf"\"(?:{_PROTECTED_TABLE_PATTERN})\"|"
    rf"`(?:{_PROTECTED_TABLE_PATTERN})`|"
    rf"\[(?:{_PROTECTED_TABLE_PATTERN})\]"
)
_OPTIONAL_SCHEMA_PATTERN = r"(?:(?:\w+|\"[^\"]+\"|`[^`]+`|\[[^\]]+\])\s*\.\s*)?"
_PROTECTED_FACT_DML_RE: Final = re.compile(
    rf"""
    \b(?:
        INSERT(?:\s+OR\s+\w+)?\s+INTO
        |REPLACE\s+INTO
        |UPDATE
        |DELETE\s+FROM
        |TRUNCATE(?:\s+TABLE)?
    )\s+
    {_OPTIONAL_SCHEMA_PATTERN}
    (?:{_QUOTED_PROTECTED_TABLE_PATTERN})
    (?=\s|\(|$|;)
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)
_CREATE_TRIGGER_BLOCK_RE: Final = re.compile(
    r"\bCREATE\s+(?:TEMP(?:ORARY)?\s+)?TRIGGER\b[\s\S]*?\bEND\s*;",
    re.IGNORECASE,
)

_FACT_TABLE_DML_ERROR: Final = (
    "Direct mutations on fact-owned tables are forbidden; "
    "use CortexEngine.store()/mutation APIs"
)


def is_protected_fact_table_dml(sql: str, *, allow_trigger_bodies: bool = False) -> bool:
    """Return True when SQL mutates fact-owned tables outside canonical storage."""
    candidate = _CREATE_TRIGGER_BLOCK_RE.sub(" ", sql) if allow_trigger_bodies else sql
    return bool(_PROTECTED_FACT_DML_RE.search(candidate))


def reject_protected_fact_table_dml(sql: str, *, allow_trigger_bodies: bool = False) -> None:
    """Fail closed for direct mutations of fact-owned persistence tables."""
    if is_protected_fact_table_dml(sql, allow_trigger_bodies=allow_trigger_bodies):
        raise ValueError(_FACT_TABLE_DML_ERROR)
