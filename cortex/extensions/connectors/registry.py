"""registry.py — ConnectorRegistry

Lazy-load registry for all CORTEX connectors.
Connectors register by system name; instances are created on demand.
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.extensions.connectors.base import BaseConnector, ConnectorConfig
from cortex.extensions.interfaces.engine import EngineProtocol

logger = logging.getLogger(__name__)

# System → connector class map (populated by register_connector())
_REGISTRY: dict[str, type[BaseConnector]] = {}


def register_connector(system: str, cls: type[BaseConnector]) -> None:
    """Register a connector class for a system name."""
    _REGISTRY[system] = cls
    logger.debug("ConnectorRegistry: registered '%s' → %s", system, cls.__name__)


def build_connector(
    config: ConnectorConfig,
    engine: EngineProtocol,
    **kwargs: Any,
) -> BaseConnector:
    """Instantiate a connector by system name from config.

    Raises KeyError if system is not registered.
    """
    system = config.system
    if system not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY))
        raise KeyError(
            f"No connector registered for system '{system}'. "
            f"Available: {available or '(none)'}"
        )
    cls = _REGISTRY[system]
    return cls(config=config, engine=engine, **kwargs)


def list_connectors() -> list[str]:
    """Return list of registered system names."""
    return sorted(_REGISTRY.keys())


class ConnectorRegistry:
    """High-level registry facade with instance lifecycle management."""

    def __init__(self, engine: EngineProtocol) -> None:
        self._engine = engine
        self._instances: dict[str, BaseConnector] = {}

    def register(self, system: str, cls: type[BaseConnector]) -> None:
        register_connector(system, cls)

    def get_or_create(self, config: ConnectorConfig, **kwargs: Any) -> BaseConnector:
        key = config.connector_id
        if key not in self._instances:
            self._instances[key] = build_connector(config, self._engine, **kwargs)
        return self._instances[key]

    def get(self, connector_id: str) -> BaseConnector | None:
        return self._instances.get(connector_id)

    def list_active(self) -> list[str]:
        return list(self._instances.keys())

    def list_available(self) -> list[str]:
        return list_connectors()
