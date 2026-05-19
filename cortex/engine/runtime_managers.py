"""Lazy runtime manager accessors for :mod:`cortex.engine`."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.consensus.manager import ConsensusManager
    from cortex.embeddings.manager import EmbeddingManager
    from cortex.engine.auth import ByzantineAuthLayer
    from cortex.engine.lock import SovereignLock
    from cortex.engine.trust_registry import TrustRegistry
    from cortex.facts.manager import FactManager
    from cortex.ledger import EnrichmentQueue, LedgerStore, LedgerWriter
    from cortex.mac_maestro.executor import MaestroExecutor


class RuntimeManagersMixin:
    """JIT manager synthesis for the composite engine."""

    if TYPE_CHECKING:
        _db_path: Path
        _facts: FactManager | None
        _embeddings: EmbeddingManager | None
        _consensus: ConsensusManager | None
        _lock_sovereign: SovereignLock | None
        _ledger_store: LedgerStore | None
        _enrichment_queue: EnrichmentQueue | None
        _ledger_writer: LedgerWriter | None
        _mac_maestro: MaestroExecutor | None
        _auth: ByzantineAuthLayer | None
        _trust_registry: TrustRegistry | None

    @property
    def facts(self) -> FactManager:
        if self._facts is None:
            from cortex.facts.manager import FactManager

            self._facts = FactManager(self)  # type: ignore[arg-type]
        return self._facts

    @facts.setter
    def facts(self, value: FactManager) -> None:
        self._facts = value

    @property
    def embeddings(self) -> EmbeddingManager:
        if self._embeddings is None:
            from cortex.embeddings.manager import EmbeddingManager

            self._embeddings = EmbeddingManager(self)
        return self._embeddings

    @embeddings.setter
    def embeddings(self, value: EmbeddingManager) -> None:
        self._embeddings = value

    @property
    def consensus(self) -> ConsensusManager:
        if self._consensus is None:
            from cortex.consensus.manager import ConsensusManager

            self._consensus = ConsensusManager(self)
        return self._consensus

    @consensus.setter
    def consensus(self, value: ConsensusManager) -> None:
        self._consensus = value

    @property
    def lock_sovereign(self) -> SovereignLock:
        if self._lock_sovereign is None:
            from cortex.engine.lock import SovereignLock

            self._lock_sovereign = SovereignLock(self)
        return self._lock_sovereign

    @lock_sovereign.setter
    def lock_sovereign(self, value: SovereignLock) -> None:
        self._lock_sovereign = value

    @property
    def auth(self) -> ByzantineAuthLayer:
        if self._auth is None:
            from cortex.engine.auth import ByzantineAuthLayer

            self._auth = ByzantineAuthLayer()
        return self._auth

    @auth.setter
    def auth(self, value: ByzantineAuthLayer) -> None:
        self._auth = value

    @property
    def ledger_store(self) -> LedgerStore:
        if self._ledger_store is None:
            from cortex.ledger import LedgerStore

            self._ledger_store = LedgerStore(self._db_path)
        return self._ledger_store

    @ledger_store.setter
    def ledger_store(self, value: LedgerStore) -> None:
        self._ledger_store = value

    @property
    def enrichment_queue(self) -> EnrichmentQueue:
        if self._enrichment_queue is None:
            from cortex.ledger import EnrichmentQueue

            self._enrichment_queue = EnrichmentQueue(self.ledger_store)
        return self._enrichment_queue

    @enrichment_queue.setter
    def enrichment_queue(self, value: EnrichmentQueue) -> None:
        self._enrichment_queue = value

    @property
    def ledger_writer(self) -> LedgerWriter:
        if self._ledger_writer is None:
            from cortex.ledger import LedgerWriter

            self._ledger_writer = LedgerWriter(self.ledger_store, self.enrichment_queue)
        return self._ledger_writer

    @ledger_writer.setter
    def ledger_writer(self, value: LedgerWriter) -> None:
        self._ledger_writer = value

    @property
    def mac_maestro(self) -> MaestroExecutor:
        if self._mac_maestro is None:
            from cortex.mac_maestro.executor import MaestroExecutor

            self._mac_maestro = MaestroExecutor(self.ledger_writer)
        return self._mac_maestro

    @mac_maestro.setter
    def mac_maestro(self, value: MaestroExecutor) -> None:
        self._mac_maestro = value

    def get_trust_registry(self) -> TrustRegistry:
        """Return the in-memory trust registry used by trust endpoints."""
        if self._trust_registry is None:
            from cortex.engine.trust_registry import TrustRegistry

            self._trust_registry = TrustRegistry()
        return self._trust_registry
