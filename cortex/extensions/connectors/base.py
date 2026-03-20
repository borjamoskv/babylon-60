"""base.py — ConnectorProtocol

Minimal contract every CORTEX connector must satisfy.
All connectors pull records from an external system and persist them
as typed facts through EngineProtocol.store() — never bypassing guards.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from cortex.extensions.interfaces.engine import EngineProtocol

logger = logging.getLogger(__name__)


@dataclass
class ConnectorConfig:
    """Runtime configuration for a connector instance.

    Credentials are NEVER stored here — they must be read from keyring
    at connect() time using the service_name as the keyring namespace.
    """

    connector_id: str
    system: str  # "salesforce" | "sap_s4hana" | "sap_b1" | "generic_rest"
    base_url: str
    tenant_id: str = "default"
    project: str = "connectors"
    # Keyring service key — credentials fetched from OS vault, not from this config
    keyring_service: str = ""
    # Pull interval in seconds (for daemon/polling mode)
    poll_interval_seconds: int = 300
    # Max records to ingest per pull cycle (circuit breaker)
    max_records_per_cycle: int = 500
    # Additional system-specific params
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestResult:
    """Result of a single connector pull cycle."""

    connector_id: str
    system: str
    records_fetched: int
    records_stored: int
    records_skipped: int
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def __str__(self) -> str:
        return (
            f"[{self.connector_id}] fetched={self.records_fetched} "
            f"stored={self.records_stored} skipped={self.records_skipped} "
            f"errors={len(self.errors)}"
        )


class BaseConnector(ABC):
    """Abstract CORTEX connector — pulls external records, stores as facts.

    Lifecycle:
        1. connect()      — authenticate, open session
        2. pull()         — fetch records from remote system
        3. ingest()       — transform records → CORTEX facts via engine.store()
        4. disconnect()   — release session / tokens

    All writes go through EngineProtocol — guards and ledger are always active.
    Subclasses must NOT call engine.store() directly from pull(); use ingest().
    """

    def __init__(self, config: ConnectorConfig, engine: EngineProtocol) -> None:
        self.config = config
        self.engine = engine

    @property
    def connector_id(self) -> str:
        return self.config.connector_id

    @abstractmethod
    async def connect(self) -> None:
        """Authenticate and open session. Reads credentials from keyring."""

    @abstractmethod
    async def pull(self) -> list[dict[str, Any]]:
        """Fetch raw records from external system. Returns native dicts."""

    @abstractmethod
    async def transform(self, record: dict[str, Any]) -> dict[str, Any] | None:
        """Transform a raw record into a CORTEX fact payload.

        Returns None to skip the record (filtered out before store()).
        Must return: {content, fact_type, tags, confidence, source, meta}
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Release session, revoke ephemeral tokens."""

    async def ingest(self) -> IngestResult:
        """Full pull-transform-store cycle. Core invariant: all writes through engine."""
        result = IngestResult(
            connector_id=self.connector_id,
            system=self.config.system,
            records_fetched=0,
            records_stored=0,
            records_skipped=0,
        )

        try:
            records = await self.pull()
        except Exception as exc:
            result.errors.append(f"pull() failed: {exc}")
            logger.error("[%s] pull() failed: %s", self.connector_id, exc)
            return result

        result.records_fetched = len(records)
        cap = self.config.max_records_per_cycle
        if len(records) > cap:
            logger.warning(
                "[%s] circuit breaker: capping %d records to %d",
                self.connector_id, len(records), cap,
            )
            records = records[:cap]

        for raw in records:
            try:
                payload = await self.transform(raw)
            except Exception as exc:
                result.errors.append(f"transform() error on record: {exc}")
                result.records_skipped += 1
                continue

            if payload is None:
                result.records_skipped += 1
                continue

            try:
                await self.engine.store(
                    project=self.config.project,
                    content=payload["content"],
                    tenant_id=self.config.tenant_id,
                    fact_type=payload.get("fact_type", "knowledge"),
                    tags=payload.get("tags"),
                    confidence=payload.get("confidence", "C3"),
                    source=payload.get("source", self.config.base_url),
                    meta=payload.get("meta"),
                )
                result.records_stored += 1
            except Exception as exc:
                result.errors.append(f"engine.store() failed: {exc}")
                result.records_skipped += 1
                logger.error("[%s] engine.store() failed: %s", self.connector_id, exc)

        logger.info("[%s] ingest complete: %s", self.connector_id, result)
        return result
