"""Sovereign Darknet (Dead-Internet Inversion).

Motor que invierte el consumo digital: descarga crudos del mundo real,
los asimila vía agentes IA y genera tu red social 100% curada localmente.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .agents import DarknetAgent
    from .ingestor import DarknetIngestor
    from .social_ledger import DarknetLedger

__all__ = ["DarknetAgent", "DarknetIngestor", "DarknetLedger"]


def __getattr__(name: str) -> object:
    """Lazily expose the public darknet symbols."""
    if name == "DarknetAgent":
        from .agents import DarknetAgent

        return DarknetAgent

    if name == "DarknetIngestor":
        from .ingestor import DarknetIngestor

        return DarknetIngestor

    if name == "DarknetLedger":
        from .social_ledger import DarknetLedger

        return DarknetLedger

    msg = f"module 'cortex.darknet' has no attribute {name!r}"
    raise AttributeError(msg)
