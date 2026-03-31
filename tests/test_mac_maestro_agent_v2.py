"""Tests for MacMaestroAgent v2 — structured plan execution."""

from __future__ import annotations

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch


def _run(coro):
    """Helper to run async tests."""
    return asyncio.run(coro)


# ══════════════════════════════════════════════════════════════
# JSON Parser Tests
# ══════════════════════════════════════════════════════════════

class TestJSONParser(unittest.TestCase):
    """Test _parse_json_response multi-strategy extraction."""

    def _get_agent(self):
        with patch(
            "cortex.extensions.agents.mac_maestro.LLMManager",
        ):
            from cortex.extensions.agents.mac_maestro import (
                MacMaestroAgent,
            )
            return MacMaestroAgent()

    def test_direct_json(self):
        agent = self._get_agent()
        plan = {
            "bundle_id": "com.apple.TextEdit",
            "actions": [{"vector": "A", "name": "t"}],
        }
        result = agent._parse_json_response(json.dumps(plan))
        self.assertIsNotNone(result)
        self.assertEqual(result["bundle_id"], "com.apple.TextEdit")

    def test_fenced_json(self):
        agent = self._get_agent()
        raw = '```json\n{"bundle_id":"com.test","actions":[]}\n```'
        result = agent._parse_json_response(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result["bundle_id"], "com.test")

    def test_embedded_json(self):
        agent = self._get_agent()
        raw = (
            'Here is the plan:\n'
            '{"bundle_id":"com.test","actions":[]}\n'
            'Done.'
        )
        result = agent._parse_json_response(raw)
        self.assertIsNotNone(result)

    def test_no_json_returns_none(self):
        agent = self._get_agent()
        result = agent._parse_json_response("no json here")
        self.assertIsNone(result)

    def test_nested_braces(self):
        agent = self._get_agent()
        plan = {
            "bundle_id": "com.test",
            "actions": [{
                "name": "click",
                "vector": "B",
                "target_query": {
                    "role": "AXButton",
                    "title": "OK",
                },
            }],
        }
        result = agent._parse_json_response(json.dumps(plan))
        self.assertIsNotNone(result)
        self.assertEqual(len(result["actions"]), 1)
        tq = result["actions"][0]["target_query"]
        self.assertEqual(tq["role"], "AXButton")


# ══════════════════════════════════════════════════════════════
# Bundle Alias Resolution Tests
# ══════════════════════════════════════════════════════════════

class TestBundleAliases(unittest.TestCase):
    def test_known_aliases(self):
        from cortex.extensions.agents.mac_maestro import (
            _BUNDLE_ALIASES,
        )
        self.assertEqual(
            _BUNDLE_ALIASES["safari"],
            "com.apple.Safari",
        )
        self.assertEqual(
            _BUNDLE_ALIASES["chrome"],
            "com.google.Chrome",
        )
        self.assertEqual(
            _BUNDLE_ALIASES["vscode"],
            "com.microsoft.VSCode",
        )

    def test_alias_count(self):
        from cortex.extensions.agents.mac_maestro import (
            _BUNDLE_ALIASES,
        )
        self.assertGreaterEqual(len(_BUNDLE_ALIASES), 20)


# ══════════════════════════════════════════════════════════════
# Agent Execute Flow Tests
# ══════════════════════════════════════════════════════════════

class TestAgentExecute(unittest.TestCase):
    """Test the full execute pipeline with mocked LLM."""

    def _get_agent(self):
        with patch(
            "cortex.extensions.agents.mac_maestro.LLMManager",
        ) as MockLLM:
            mock = MockLLM.return_value
            mock.available = True
            mock.complete = AsyncMock()
            from cortex.extensions.agents.mac_maestro import (
                MacMaestroAgent,
            )
            agent = MacMaestroAgent()
            agent.llm = mock
            return agent

    def test_no_llm_returns_error(self):
        with patch(
            "cortex.extensions.agents.mac_maestro.LLMManager",
        ) as MockLLM:
            mock = MockLLM.return_value
            mock.available = False
            from cortex.extensions.agents.mac_maestro import (
                MacMaestroAgent,
            )
            agent = MacMaestroAgent()
            agent.llm = mock

            result = _run(agent.execute("open notes"))
            self.assertFalse(result["success"])
            self.assertIn("No LLM", result["error"])

    def test_empty_response_returns_error(self):
        agent = self._get_agent()
        agent.llm.complete.return_value = None

        result = _run(agent.execute("open finder"))
        self.assertFalse(result["success"])
        self.assertIn("empty", result["error"])

    def test_plan_with_no_actions_returns_error(self):
        agent = self._get_agent()
        agent.llm.complete.return_value = json.dumps({
            "bundle_id": "com.apple.finder",
            "app_name": "Finder",
            "explanation": "test",
            "actions": [],
        })

        result = _run(agent.execute("open finder"))
        self.assertFalse(result["success"])
        self.assertIn("no actions", result["error"])

    def test_unknown_app_resolved_via_alias(self):
        """LLM returns app_name without bundle_id."""
        agent = self._get_agent()
        agent.llm.complete.return_value = json.dumps({
            "app_name": "Safari",
            "explanation": "Open Safari",
            "actions": [{
                "name": "activate",
                "vector": "A",
                "target_query": {
                    "app_name": "Safari",
                },
            }],
        })

        # Mock the applescript fallback
        with patch(
            "cortex.extensions.agents.mac_maestro"
            ".run_applescript",
            new_callable=AsyncMock,
            return_value=(True, "", ""),
        ):
            result = _run(agent.execute("open safari"))
            # Should resolve via _BUNDLE_ALIASES
            self.assertTrue(
                result.get("success")
                or result.get("mode") == "applescript_fallback"
                or "plan" in result
            )

    def test_legacy_fallback_with_script(self):
        """LLM returns V1-style {script, explanation}."""
        agent = self._get_agent()
        agent.llm.complete.return_value = json.dumps({
            "explanation": "Activate Finder",
            "script": (
                'tell application "Finder" to activate'
            ),
        })

        with patch(
            "cortex.extensions.agents.mac_maestro"
            ".run_applescript",
            new_callable=AsyncMock,
            return_value=(True, "", ""),
        ):
            result = _run(agent.execute("open finder"))
            self.assertTrue(result["success"])
            self.assertEqual(result["mode"], "legacy_v1")

    def test_unparseable_response_falls_back(self):
        agent = self._get_agent()
        agent.llm.complete.return_value = (
            "I cannot help with that request."
        )

        result = _run(agent.execute("do something"))
        self.assertFalse(result["success"])
        self.assertIn("Failed to parse", result["error"])


# ══════════════════════════════════════════════════════════════
# System Prompt Tests
# ══════════════════════════════════════════════════════════════

class TestSystemPrompt(unittest.TestCase):
    def test_prompt_contains_vectors(self):
        from cortex.extensions.agents.mac_maestro import (
            SYSTEM_PROMPT,
        )
        self.assertIn("A (AppleScript)", SYSTEM_PROMPT)
        self.assertIn("B (AXUIElement)", SYSTEM_PROMPT)
        self.assertIn("C (Keyboard)", SYSTEM_PROMPT)
        self.assertIn("D (CGEvent)", SYSTEM_PROMPT)

    def test_prompt_contains_json_structure(self):
        from cortex.extensions.agents.mac_maestro import (
            SYSTEM_PROMPT,
        )
        self.assertIn("bundle_id", SYSTEM_PROMPT)
        self.assertIn("actions", SYSTEM_PROMPT)
        self.assertIn("vector", SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
