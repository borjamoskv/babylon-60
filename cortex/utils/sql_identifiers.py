# [C5-REAL] Exergy-Maximized
import re

_SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}\Z")


def validate_sql_identifier(name: str) -> str:
    """Raise ValueError if name is not a safe SQL identifier."""
    if not _SAFE_IDENTIFIER.match(name):
        raise ValueError(f"Unsafe SQL identifier rejected: {name!r}")
    return name
