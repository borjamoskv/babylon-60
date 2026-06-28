# [C5-REAL] Exergy-Maximized
"""
Verification tests for Host Identity Containment (Epoch 13).
"""
import pytest

from cortex.engine.causal.taint_engine import enforce_taint_check, TaintValidationError


@pytest.mark.asyncio
async def test_pii_clean_payload_passes():
    """Verify that a clean payload does not raise any PII exceptions."""
    # Should not raise
    await enforce_taint_check(conn=None, token=None, content="Clean payload representing factual state.")


@pytest.mark.asyncio
async def test_pii_literal_leak_blocked():
    """Verify that literal name strings are strictly blocked."""
    with pytest.raises(TaintValidationError) as excinfo:
        await enforce_taint_check(conn=None, token=None, content="This fact belongs to borja fernandez angulo.")
    assert "Host Identity PII" in str(excinfo.value)


@pytest.mark.asyncio
async def test_pii_accented_leak_blocked():
    """Verify that unicode variations with diacritics / accents are blocked."""
    with pytest.raises(TaintValidationError):
        await enforce_taint_check(conn=None, token=None, content="Fact by Borja Fernández Angulo.")


@pytest.mark.asyncio
async def test_pii_obfuscated_leak_blocked():
    """Verify that obfuscated strings like dashes or dots are blocked."""
    with pytest.raises(TaintValidationError):
        await enforce_taint_check(conn=None, token=None, content="user: borja-fernandez-angulo")
        
    with pytest.raises(TaintValidationError):
        await enforce_taint_check(conn=None, token=None, content="path: /users/borja_fernandez_angulo/data")


@pytest.mark.asyncio
async def test_pii_proximity_leak_blocked():
    """Verify that co-occurrence of name tokens is blocked."""
    with pytest.raises(TaintValidationError):
        await enforce_taint_check(
            conn=None, 
            token=None, 
            content="Borja went to the store. Fernandez was also there."
        )
