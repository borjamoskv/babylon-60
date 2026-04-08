"""Tests for the CORTEX ADK runner wiring."""

from argparse import Namespace


class TestADKRunner:
    """Test CLI parsing and domain-agent propagation."""

    def test_parse_domain_agents_flattens_csv_and_preserves_none(self):
        """Repeatable CLI values should flatten cleanly for the swarm builder."""
        from cortex.extensions.adk.runner import _parse_domain_agents

        assert _parse_domain_agents(None) is None
        assert _parse_domain_agents(["Finance, routing", "legal_ops", " "]) == [
            "Finance",
            "routing",
            "legal_ops",
        ]

    def test_main_passes_domain_agents_to_run_cli(self, monkeypatch):
        """Main should forward parsed domain agents to the sovereign runner."""
        import cortex.extensions.adk.runner as adk_runner

        captured = {}

        monkeypatch.setattr(
            adk_runner,
            "_parse_args",
            lambda: Namespace(
                agent="sovereign",
                model="gemini-2.0-flash",
                domain_agents=["security, routing", "legal_ops"],
                web=False,
                port=8000,
                toolbox_url=None,
                toolbox_toolset="",
            ),
        )
        monkeypatch.setattr(adk_runner, "run_web", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            adk_runner,
            "run_cli",
            lambda **kwargs: captured.update(kwargs),
        )

        adk_runner.main()

        assert captured["agent_name"] == "sovereign"
        assert captured["domain_agents"] == ["security", "routing", "legal_ops"]
