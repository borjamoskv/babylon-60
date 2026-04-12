"""Tests for MemoryMixin continual-learning bootstrap wiring."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

import pytest

from cortex.engine.memory_mixin import MemoryMixin
from cortex.extensions.continual_learning import MLXLoRABackend


class _DummyEmbedder:
    """Synchronous embedder stub accepted by the continual-learning sidecar."""

    def embed(self, text: str) -> list[float]:
        return [float(len(text)), 1.0]


class _TestMemoryEngine(MemoryMixin):
    """Minimal engine shell for exercising the memory bootstrap path."""

    def __init__(self) -> None:
        self._auto_embed = True
        self._embedder = _DummyEmbedder()
        self._memory_manager = None
        self._memory_l1 = None
        self._memory_l3 = None

    def _get_embedder(self) -> _DummyEmbedder:
        return self._embedder

    def _get_sync_conn(self) -> object:
        return object()


class _FakeEventLedgerL3:
    """Lightweight ledger stub for bootstrap tests."""

    def __init__(self, conn: object) -> None:
        self.conn = conn

    async def ensure_table(self) -> None:
        return None


class _FakeSignalBus:
    """Lightweight durable bus stub for bootstrap tests."""

    def __init__(self, conn: object) -> None:
        self.conn = conn

    def ensure_table(self) -> None:
        return None


class _FakeAsyncEncoder:
    """Encoder stub that preserves the injected embedder reference."""

    def __init__(self, embedder: object) -> None:
        self.embedder = embedder


class _FakeVectorStore:
    """Vector store stub that captures its database path."""

    def __init__(self, *, encoder: object, db_path: Path) -> None:
        self.encoder = encoder
        self.db_path = db_path


class _FakeManager:
    """Capture the exact kwargs MemoryMixin passes into CortexMemoryManager."""

    last_instance: _FakeManager | None = None

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        _FakeManager.last_instance = self


def _module(name: str, **attrs: object) -> ModuleType:
    """Build a simple importable module for monkeypatching dynamic imports."""
    module = ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    return module


def _install_memory_bootstrap_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch the modules imported lazily inside MemoryMixin._init_memory_subsystem."""
    monkeypatch.setitem(
        sys.modules,
        "cortex.memory.ledger",
        _module("cortex.memory.ledger", EventLedgerL3=_FakeEventLedgerL3),
    )
    monkeypatch.setitem(
        sys.modules,
        "cortex.memory.working",
        _module("cortex.memory.working", WorkingMemoryL1=type("WorkingMemoryL1", (), {})),
    )
    monkeypatch.setitem(
        sys.modules,
        "cortex.extensions.signals.bus",
        _module("cortex.extensions.signals.bus", DurableSignalBus=_FakeSignalBus),
    )
    monkeypatch.setitem(
        sys.modules,
        "cortex.memory.encoder",
        _module("cortex.memory.encoder", AsyncEncoder=_FakeAsyncEncoder),
    )
    monkeypatch.setitem(
        sys.modules,
        "cortex.memory.sqlite_vec_store",
        _module("cortex.memory.sqlite_vec_store", SovereignVectorStoreL2=_FakeVectorStore),
    )
    monkeypatch.setitem(
        sys.modules,
        "cortex.memory.manager",
        _module("cortex.memory.manager", CortexMemoryManager=_FakeManager),
    )


@pytest.mark.asyncio
async def test_memory_mixin_autowires_continual_backend_when_env_is_complete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MemoryMixin should inject an execution backend only when env config is complete."""
    _install_memory_bootstrap_stubs(monkeypatch)
    monkeypatch.setenv("CORTEX_CONTINUAL_LEARNING", "1")
    monkeypatch.setenv("CORTEX_CONTINUAL_LEARNING_DB_PATH", str(tmp_path / "continual_learning.db"))
    monkeypatch.setenv("CORTEX_CONTINUAL_LEARNING_BACKEND", "mlx")
    monkeypatch.setenv("CORTEX_CONTINUAL_LEARNING_BASE_MODEL", "mlx-community/test-model")
    monkeypatch.setenv(
        "CORTEX_CONTINUAL_LEARNING_SCORE_COMMAND",
        f"{sys.executable} -c \"print('unused during bootstrap')\"",
    )
    monkeypatch.setenv("CORTEX_CONTINUAL_LEARNING_WORK_DIR", str(tmp_path / "runs"))
    monkeypatch.setenv("CORTEX_CONTINUAL_LEARNING_DRY_RUN", "1")

    engine = _TestMemoryEngine()
    await engine._init_memory_subsystem(tmp_path / "memory.db", object())

    manager = _FakeManager.last_instance
    assert manager is not None
    assert manager.kwargs["continual_learning"] is not None
    assert isinstance(manager.kwargs["continual_training_backend"], MLXLoRABackend)


@pytest.mark.asyncio
async def test_memory_mixin_keeps_sidecar_but_disables_backend_on_incomplete_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MemoryMixin should fail closed on backend misconfiguration without dropping the sidecar."""
    _install_memory_bootstrap_stubs(monkeypatch)
    monkeypatch.setenv("CORTEX_CONTINUAL_LEARNING", "1")
    monkeypatch.setenv("CORTEX_CONTINUAL_LEARNING_DB_PATH", str(tmp_path / "continual_learning.db"))
    monkeypatch.setenv("CORTEX_CONTINUAL_LEARNING_BACKEND", "mlx")
    monkeypatch.setenv("CORTEX_CONTINUAL_LEARNING_BASE_MODEL", "mlx-community/test-model")

    engine = _TestMemoryEngine()
    await engine._init_memory_subsystem(tmp_path / "memory.db", object())

    manager = _FakeManager.last_instance
    assert manager is not None
    assert manager.kwargs["continual_learning"] is not None
    assert manager.kwargs["continual_training_backend"] is None
