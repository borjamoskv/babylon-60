"""Lazy manager accessors for the composite CORTEX engine."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.consensus.manager import ConsensusManager
    from cortex.embeddings.manager import EmbeddingManager
    from cortex.engine.auth import ByzantineAuthLayer
    from cortex.engine.lock import SovereignLock
    from cortex.engine.trust_registry import TrustRegistry
    from cortex.facts.manager import FactManager
    from cortex.ledger import EnrichmentQueue, LedgerStore, LedgerWriter
    from cortex.mac_maestro.executor import MaestroExecutor


class ManagerAccessorsMixin:
    @property
    def facts(self) -> FactManager:  # noqa: F821
        if self._facts is None:
            from cortex.facts.manager import FactManager

            self._facts = FactManager(self)  # type: ignore
        return self._facts

    @facts.setter
    def facts(self, value: FactManager) -> None:  # noqa: F821
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
    def auth(self) -> ByzantineAuthLayer:  # noqa: F821
        if self._auth is None:
            from cortex.engine.auth import ByzantineAuthLayer

            self._auth = ByzantineAuthLayer()
        return self._auth

    @auth.setter
    def auth(self, value: ByzantineAuthLayer) -> None:  # noqa: F821
        self._auth = value

    @property
    def ledger_store(self) -> LedgerStore:
        if self._ledger_store is None:
            from cortex.ledger import LedgerStore

            engine: Any = self
            self._ledger_store = LedgerStore(engine._db_path)
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
