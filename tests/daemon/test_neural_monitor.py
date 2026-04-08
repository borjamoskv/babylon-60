from __future__ import annotations

from cortex.extensions.agents.neural import NeuralContext, NeuralHypothesis
from cortex.extensions.daemon.monitors.neural import NeuralIntentMonitor


class _FakeNeuralEngine:
    def read_context(self) -> tuple[NeuralContext, str]:
        return (
            NeuralContext(
                active_window="Chrome",
                clipboard_hash="abc",
                clipboard_entropy=2.0,
                timestamp=123.0,
            ),
            "click #submit",
        )

    def infer_intent(
        self, context: NeuralContext, raw_clipboard: str = ""
    ) -> NeuralHypothesis | None:
        assert context.active_window == "Chrome"
        assert raw_clipboard == "click #submit"
        return NeuralHypothesis(
            intent="mac_control_browser_flow",
            confidence="C4",
            trigger="Browser automation or CDP control pattern detected in clipboard",
            summary="Inferred browser control flow",
        )


def test_neural_monitor_builds_alert_from_engine(monkeypatch) -> None:
    monkeypatch.setattr("cortex.extensions.platform.sys.is_macos", lambda: True)
    monkeypatch.setattr(
        "cortex.extensions.agents.neural.NeuralIntentEngine",
        _FakeNeuralEngine,
    )

    alerts = NeuralIntentMonitor().check()

    assert len(alerts) == 1
    assert alerts[0].intent == "mac_control_browser_flow"
    assert alerts[0].confidence == "C4"
