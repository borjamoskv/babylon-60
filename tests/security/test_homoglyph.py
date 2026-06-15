# [C5-REAL] Exergy-Maximized
import pytest

from cortex.security.homoglyph import HomoglyphGuard
from cortex.security.types import GuardViolation


def test_clean_text_passes():
    """Verify that normal English and Spanish texts pass the validation."""
    assert HomoglyphGuard.validate("This is standard English text.") is True
    assert HomoglyphGuard.validate("Este es un texto estándar en español.") is True
    assert HomoglyphGuard.validate("Normal numbers 12345 and punctuation! (parentheses)") is True


def test_homoglyph_detection_cyrillic():
    """Verify that homoglyphs mixing Cyrillic and Latin characters are detected."""
    # 'dеfensа' uses Cyrillic 'е' (U+0435) and Cyrillic 'а' (U+0430)
    assert HomoglyphGuard.validate("Using dеfensа to bypass guardrails.") is False


def test_homoglyph_detection_greek():
    """Verify that homoglyphs mixing Greek and Latin characters are detected."""
    # 'cοntent' uses Greek Omicron 'ο' (U+03BF)
    assert HomoglyphGuard.validate("This cοntent is malicious.") is False


def test_enforce_raises_guard_violation():
    """Verify that the enforce method raises GuardViolation on detection."""
    with pytest.raises(GuardViolation, match="Input rejected: Homoglyph/Mixed-script bypass attempt detected."):
        HomoglyphGuard.enforce("This cοntent is malicious.")


def test_clean_single_script_words_pass():
    """Verify that words constructed entirely of a single script (even if non-Latin) pass."""
    # "дефенса" is entirely Cyrillic
    assert HomoglyphGuard.validate("дефенса") is True
    # "logos" in Greek characters (λόγος)
    assert HomoglyphGuard.validate("λόγος") is True


def test_empty_content_passes():
    """Verify that empty or whitespace-only content passes."""
    assert HomoglyphGuard.validate("") is True
    assert HomoglyphGuard.validate("   \n\t  ") is True
