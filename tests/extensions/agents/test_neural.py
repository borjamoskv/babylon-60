from __future__ import annotations

import json

from cortex.extensions.agents import neural


def test_engine_merges_mac_control_defaults_into_existing_rule_file(tmp_path, monkeypatch) -> None:
    rules_path = tmp_path / "neural_rules.json"
    rules_path.write_text(
        json.dumps(
            [
                {
                    "app_re": r"(Chrome)",
                    "clip_re": r"^https?://",
                    "intent": "researching",
                    "confidence": "C3",
                    "trigger_desc": "URL copied while in browser",
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(neural, "get_cortex_dir", lambda: tmp_path)

    engine = neural.NeuralIntentEngine()
    context = neural.NeuralContext(
        active_window="Chrome",
        clipboard_hash="abc",
        clipboard_entropy=3.0,
        timestamp=100.0,
    )

    hypothesis = engine.infer_intent(context, "document.querySelector('#submit').click()")

    assert hypothesis is not None
    assert hypothesis.intent == "mac_control_browser_flow"
    assert "CDP control" in hypothesis.trigger


def test_engine_detects_mac_control_verification_loop(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(neural, "get_cortex_dir", lambda: tmp_path)

    engine = neural.NeuralIntentEngine()
    context = neural.NeuralContext(
        active_window="Cursor",
        clipboard_hash="def",
        clipboard_entropy=2.5,
        timestamp=200.0,
    )

    hypothesis = engine.infer_intent(
        context,
        "  wait_for_selector('#toast') and assert the Saved toast is ready  ",
    )

    assert hypothesis is not None
    assert hypothesis.intent == "mac_control_verification_loop"
    assert hypothesis.confidence == "C3"
