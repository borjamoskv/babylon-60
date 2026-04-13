from __future__ import annotations

import urllib.error

import pytest


def test_sanitizer_rejects_untrusted_external_script_without_sri() -> None:
    from cortex.engine.membrane.sanitizer import SovereignSanitizer

    raw_engram = {
        "type": "decision",
        "source": "agent:test",
        "topic": "proj",
        "content": '<script src="https://evil.example/payload.js"></script>',
        "metadata": {},
    }

    with pytest.raises(ValueError, match="External resource rejected by SRI membrane"):
        SovereignSanitizer.digest(raw_engram)


def test_sanitizer_rejects_trusted_external_script_when_sri_fetch_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cortex.engine.membrane import sri_hash
    from cortex.engine.membrane.sanitizer import SovereignSanitizer

    def fail_urlopen(*args, **kwargs):
        raise urllib.error.URLError("network down")

    sri_hash.generate_sri_hash.cache_clear()
    monkeypatch.setattr(sri_hash.urllib.request, "urlopen", fail_urlopen)

    raw_engram = {
        "type": "decision",
        "source": "agent:test",
        "topic": "proj",
        "content": '<script src="https://cdn.jsdelivr.net/npm/lib.js"></script>',
        "metadata": {},
    }

    with pytest.raises(ValueError, match="Failed to fetch SRI"):
        SovereignSanitizer.digest(raw_engram)
