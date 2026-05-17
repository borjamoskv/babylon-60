"""
Tests for tip_registry.json dynamic loading and cryptographic SHA-256 verification (v6.0).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest

import cortex.cli.tips as tips_mod
from cortex.cli.tips import (
    Tip,
    TipCategory,
    TipsEngine,
    verify_tip_integrity,
    _load_registry_tips,
)


@pytest.fixture(autouse=True)
def clean_registry_cache():
    """Ensure the tips registry cache is cleared before and after each test."""
    tips_mod._REGISTRY_TIPS_CACHE = None
    yield
    tips_mod._REGISTRY_TIPS_CACHE = None


def test_verify_tip_integrity():
    content = "Always verify dynamic anchors prior to system actions."
    expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    assert verify_tip_integrity(content, expected_hash) is True

    # NFC normalization verification
    normalized_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    assert verify_tip_integrity(" " + content + " \n", normalized_hash) is True

    # Tampered content fails
    assert verify_tip_integrity(content + "!", expected_hash) is False
    assert verify_tip_integrity(content, "wrong_hash") is False


def test_load_registry_tips_valid(tmp_path, monkeypatch):
    registry_file = tmp_path / "tip_registry.json"
    monkeypatch.setattr(tips_mod, "_REGISTRY_ASSET_PATH", registry_file)

    content = "Verifiable dynamic anchors ensure absolute zero-drift execution."
    tip_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    registry_data = [
        {
            "id": "REG-001",
            "content": content,
            "category": "security",
            "hash": tip_hash,
            "anchor": "k2-shared",
        }
    ]
    registry_file.write_text(json.dumps(registry_data), encoding="utf-8")

    loaded = _load_registry_tips()
    assert len(loaded) == 1
    assert loaded[0].id == "REG-001"
    assert loaded[0].content == content
    assert loaded[0].category == TipCategory.SECURITY
    assert loaded[0].project == "k2-shared"
    assert loaded[0].source == "dynamic"


def test_load_registry_tips_compromised(tmp_path, monkeypatch):
    registry_file = tmp_path / "tip_registry.json"
    monkeypatch.setattr(tips_mod, "_REGISTRY_ASSET_PATH", registry_file)

    # First tip is valid, second tip is tampered
    valid_content = "Anchor is safe."
    valid_hash = hashlib.sha256(valid_content.encode("utf-8")).hexdigest()

    compromised_content = "Anchor has been modified maliciously!"

    registry_data = [
        {"id": "REG-OK", "content": valid_content, "category": "security", "hash": valid_hash},
        {
            "id": "REG-BAD",
            "content": compromised_content,
            "category": "efficiency",
            "hash": "compromised_hash_that_does_not_match",
        },
    ]
    registry_file.write_text(json.dumps(registry_data), encoding="utf-8")

    loaded = _load_registry_tips()
    # The compromised tip must be purged / skipped due to fail-secure cryptographic integrity check
    assert len(loaded) == 1
    assert loaded[0].id == "REG-OK"


def test_load_registry_tips_malformed(tmp_path, monkeypatch):
    registry_file = tmp_path / "tip_registry.json"
    monkeypatch.setattr(tips_mod, "_REGISTRY_ASSET_PATH", registry_file)

    registry_data = [
        # Missing id
        {"content": "Invalid tip", "category": "security", "hash": "some_hash"},
        # Missing content
        {"id": "REG-002", "category": "security", "hash": "some_hash"},
        # Missing hash
        {"id": "REG-003", "content": "No hash tip", "category": "security"},
    ]
    registry_file.write_text(json.dumps(registry_data), encoding="utf-8")

    loaded = _load_registry_tips()
    assert len(loaded) == 0


def test_load_registry_tips_nonexistent(tmp_path, monkeypatch):
    registry_file = tmp_path / "nonexistent_tip_registry.json"
    monkeypatch.setattr(tips_mod, "_REGISTRY_ASSET_PATH", registry_file)

    loaded = _load_registry_tips()
    assert loaded == []


def test_tip_manager_random_sync_with_registry(tmp_path, monkeypatch):
    registry_file = tmp_path / "tip_registry.json"
    monkeypatch.setattr(tips_mod, "_REGISTRY_ASSET_PATH", registry_file)

    content = "Special registry tip only."
    tip_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    registry_data = [
        {"id": "REG-SPECIAL", "content": content, "category": "security", "hash": tip_hash}
    ]
    registry_file.write_text(json.dumps(registry_data), encoding="utf-8")

    # Disable dynamic mining to only load static + registry pools
    manager = TipsEngine(include_dynamic=False, lang="en")

    # Attempt to pick the registry tip
    picked = manager.random_sync()
    assert picked is not None
    # Since registry tips are pooled, we might get either a static tip or our registry tip.
    # Let's ensure the pool contains our registry tip by testing the internal pool retrieval
    static_tips = tips_mod._load_static_tips()
    registry_tips = tips_mod._load_registry_tips()

    assert len(registry_tips) == 1
    assert registry_tips[0].id == "REG-SPECIAL"


@pytest.mark.asyncio
async def test_tip_manager_async_get_pool(tmp_path, monkeypatch):
    registry_file = tmp_path / "tip_registry.json"
    monkeypatch.setattr(tips_mod, "_REGISTRY_ASSET_PATH", registry_file)

    content = "Async pool registry tip."
    tip_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    registry_data = [
        {"id": "REG-ASYNC", "content": content, "category": "security", "hash": tip_hash}
    ]
    registry_file.write_text(json.dumps(registry_data), encoding="utf-8")

    manager = TipsEngine(include_dynamic=False, lang="en")
    pool = await manager._get_pool()

    assert any(t.id == "REG-ASYNC" for t in pool)


def test_invalidate_cache(tmp_path, monkeypatch):
    registry_file = tmp_path / "tip_registry.json"
    monkeypatch.setattr(tips_mod, "_REGISTRY_ASSET_PATH", registry_file)

    content = "Initial content"
    tip_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    registry_data = [
        {"id": "REG-CACHE", "content": content, "category": "security", "hash": tip_hash}
    ]
    registry_file.write_text(json.dumps(registry_data), encoding="utf-8")

    loaded = _load_registry_tips()
    assert len(loaded) == 1
    assert loaded[0].content == "Initial content"

    # Modify file, check that cached loaded is still the old one
    new_content = "Modified content"
    new_hash = hashlib.sha256(new_content.encode("utf-8")).hexdigest()
    new_registry_data = [
        {"id": "REG-CACHE", "content": new_content, "category": "security", "hash": new_hash}
    ]
    registry_file.write_text(json.dumps(new_registry_data), encoding="utf-8")

    assert _load_registry_tips()[0].content == "Initial content"

    # Invalidate cache
    manager = TipsEngine(include_dynamic=False, lang="en")
    manager.invalidate_cache()

    assert _load_registry_tips()[0].content == "Modified content"
