"""Neural intent monitor for MOSKV daemon."""

from __future__ import annotations

import logging
import re

from cortex.extensions.daemon.models import NeuralIntentAlert

logger = logging.getLogger("moskv-daemon")
_CONFIDENCE_RE = re.compile(r"(\d+)")


class NeuralIntentMonitor:
    """Reads system context and infers user intent via NeuralIntentEngine."""

    def __init__(self) -> None:
        self._engine = None

    @staticmethod
    def _confidence_score(confidence: str) -> int:
        match = _CONFIDENCE_RE.search(confidence)
        return int(match.group(1)) if match else 0

    def check(self) -> list[NeuralIntentAlert]:
        alerts: list[NeuralIntentAlert] = []
        try:
            from cortex.extensions.agents.neural import NeuralIntentEngine
            from cortex.extensions.platform.sys import is_macos

            if not is_macos():
                return []

            if not self._engine:
                self._engine = NeuralIntentEngine()

            context, raw_clip = self._engine.read_context()
            hyp = self._engine.infer_intent(context, raw_clip)

            if hyp and self._confidence_score(hyp.confidence) > 0:
                alerts.append(
                    NeuralIntentAlert(
                        intent=hyp.intent,
                        confidence=hyp.confidence,
                        trigger=hyp.trigger,
                        summary=hyp.summary,
                    )
                )
        except (ImportError, TypeError, ValueError, OSError, RuntimeError) as e:
            logger.error("NeuralIntentMonitor failed: %s", e)

        return alerts
