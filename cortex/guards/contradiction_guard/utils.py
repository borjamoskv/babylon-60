from __future__ import annotations

import re
import functools
from collections.abc import Callable

from cortex.utils.void_vec import cosine_similarity
from .constants import (
    _STOP_WORDS,
    _NEGATION_MARKERS,
    _SUPERSESSION_MARKERS,
    _VERSION_PATTERN,
    _NOISE_PREFIXES,
    TokenSet,
)

_embedding_cosine_similarity = cosine_similarity

@functools.lru_cache(maxsize=1024)
def _tokenize(text: str) -> TokenSet:
    """Extract meaningful tokens from content."""
    try:
        tokens = set(re.findall(r"[a-záéíóúñ]{3,}", text.lower()))
        return tokens - _STOP_WORDS
    except (TypeError, ValueError):
        return set()

def _jaccard(a: TokenSet, b: TokenSet) -> float:
    """Jaccard similarity coefficient."""
    if not a or not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0

def _detect_negation(content: str) -> bool:
    """Check if content contains negation/prohibition language."""
    try:
        content_lower = content.lower()
        return any(marker in content_lower for marker in _NEGATION_MARKERS)
    except (AttributeError, TypeError):
        return False

def _detect_supersession(content: str) -> bool:
    """Check if content contains supersession language."""
    try:
        return bool(_SUPERSESSION_MARKERS.search(content))
    except TypeError:
        return False

@functools.lru_cache(maxsize=1024)
def _extract_versions(content: str) -> list[str]:
    """Extract version numbers from content."""
    try:
        return _VERSION_PATTERN.findall(content)
    except TypeError:
        return []

def _is_noise(content: str) -> bool:
    """Filter out noise decisions like MAILTV archives."""
    try:
        return any(content.startswith(prefix) for prefix in _NOISE_PREFIXES)
    except AttributeError:
        return True

def _decrypt_content(content: str, decrypt_fn: Callable[[str], str] | None) -> str | None:
    """Decrypt content if needed, returning None on failure."""
    if not isinstance(content, str):
        return None
    if not decrypt_fn or not content.startswith("v6_aesgcm:"):
        return content
    try:
        return decrypt_fn(content)
    except (ValueError, TypeError, OSError):
        return None

def _classify_conflict(
    new_content: str,
    existing_content: str,
    new_tokens: TokenSet,
    existing_tokens: TokenSet,
    base_score: float,
) -> tuple[str, float]:
    """Classify conflict type and apply score multipliers."""
    conflict_type = "keyword_overlap"

    if _detect_negation(new_content) or _detect_negation(existing_content):
        conflict_type = "negation"
        base_score *= 1.5

    if _detect_supersession(new_content) or _detect_supersession(existing_content):
        conflict_type = "version_supersede"
        base_score *= 1.2

    new_versions = _extract_versions(new_content)
    old_versions = _extract_versions(existing_content)
    if new_versions and old_versions and len(new_tokens & existing_tokens) > 5:
        conflict_type = "version_supersede"
        base_score *= 1.4

    return conflict_type, base_score
