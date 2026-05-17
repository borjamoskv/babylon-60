"""Cross-platform notifications for MOSKV-1 daemon.

Dispatches to the native notification system:
- macOS:   osascript (AppleScript)
- Linux:   notify-send (libnotify)
- Windows: PowerShell toast fallback
"""

from __future__ import annotations

import logging

from cortex.extensions.daemon.models import GhostAlert, MemoryAlert, SiteStatus

__all__ = ["Notifier"]

logger = logging.getLogger("moskv-daemon")


class Notifier:
    """Native notifications via centralized NotificationBus."""

    @staticmethod
    def notify(title: str, message: str, sound: str = "Submarine") -> bool:
        """Send a notification via the NotificationBus. Returns True on success."""
        try:
            import asyncio
            from cortex.extensions.notifications.bus import get_notification_bus
            from cortex.extensions.notifications.events import CortexEvent, EventSeverity

            bus = get_notification_bus()
            severity = EventSeverity.ERROR if sound == "Basso" else EventSeverity.INFO

            event = CortexEvent(
                severity=severity,
                title=title,
                body=message,
                source="moskv-daemon",
                project="cortex",
            )

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(bus.emit(event))
            except RuntimeError:
                asyncio.run(bus.emit(event))
            return True
        except Exception as e:
            logger.warning("Notification bus dispatch failed: %s", e)
            return False

    @staticmethod
    def alert_site_down(site: SiteStatus) -> None:
        Notifier.notify(
            "⚠️ MOSKV-1 — Site Down",
            f"{site.url} is unreachable: {site.error or f'HTTP {site.status_code}'}",
            sound="Basso",
        )

    @staticmethod
    def alert_stale_project(ghost: GhostAlert) -> None:
        hours = int(ghost.hours_stale)
        Notifier.notify(
            "💤 MOSKV-1 — Proyecto Stale",
            f"{ghost.project} lleva {hours}h sin actividad",
        )

    @staticmethod
    def alert_memory_stale(alert: MemoryAlert) -> None:
        hours = int(alert.hours_stale)
        Notifier.notify(
            "🧠 MOSKV-1 — CORTEX Stale",
            f"{alert.file} sin actualizar ({hours}h). Ejecuta /memoria",
        )
