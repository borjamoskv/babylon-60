"""CORTEX — Notification Adapters registry."""

from cortex.experimental.extensions.notifications.adapters.base import BaseAdapter
from cortex.experimental.extensions.notifications.adapters.macos import MacOSAdapter
from cortex.experimental.extensions.notifications.adapters.telegram import TelegramAdapter

__all__ = [
    "BaseAdapter",
    "MacOSAdapter",
    "TelegramAdapter",
]
