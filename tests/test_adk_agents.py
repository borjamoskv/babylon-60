"""Tests for CORTEX ADK Agent Definitions.

Tests agent creation, tool registration, and configuration
without requiring Google ADK or a Gemini API key.
"""

import subprocess
import sys
from types import SimpleNamespace

import pytest


class TestADKModuleImport:
    """Test the ADK module can be imported."""

    def test_adk_package_import(self):
        """ADK package should be importable."""
        import cortex.adk  # noqa: F401

    def test_tools_module_import(self):
        """Tools module should be importable."""
        from cortex.adk import tools as adk_tools

        assert hasattr(adk_tools, "adk_store")
        assert hasattr(adk_tools, "adk_search")
        assert hasattr(adk_tools, "adk_status")
        assert hasattr(adk_tools, "adk_ledger_verify")
        assert hasattr(adk_tools, "adk_deprecate")
        assert hasattr(adk_tools, "ALL_TOOLS")

    def test_all_tools_list(self):
        """ALL_TOOLS should contain all 4 tool functions."""
        from cortex.adk.tools import ALL_TOOLS

        assert len(ALL_TOOLS) == 5
        names = [f.__name__ for f in ALL_TOOLS]
        assert "adk_store" in names
        assert "adk_search" in names
        assert "adk_status" in names
        assert "adk_ledger_verify" in names
        assert "adk_deprecate" in names

    def test_agents_module_import(self):
        """Agents module should be importable."""
        from cortex.adk import agents as adk_agents

        assert hasattr(adk_agents, "create_memory_agent")
        assert hasattr(adk_agents, "create_analyst_agent")
        assert hasattr(adk_agents, "create_guardian_agent")
        assert hasattr(adk_agents, "create_cortex_swarm")
        assert hasattr(adk_agents, "create_domain_agent")
        assert hasattr(adk_agents, "resolve_domain_agents")
        assert hasattr(adk_agents, "is_adk_available")

    def test_agents_module_import_does_not_eager_load_google_adk(self):
        """Importing the wrapper should not eagerly import Google ADK/genai."""
        script = """
import sys
import cortex.adk.agents
print("google.adk" in sys.modules)
print("google.genai" in sys.modules)
"""
        result = subprocess.run(
            [sys.executable, "-W", "error::DeprecationWarning", "-c", script],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout.strip().splitlines() == ["False", "False"]

    def test_runner_module_import(self):
        """Runner module should be importable."""
        from cortex.adk import runner as adk_runner

        assert hasattr(adk_runner, "main")
        assert hasattr(adk_runner, "run_cli")


class TestADKTools:
    """Test ADK tool function signatures and docstrings."""

    def test_adk_store_signature(self):
        """adk_store should accept expected parameters."""
        import inspect

        from cortex.adk.tools import adk_store

        sig = inspect.signature(adk_store)
        params = list(sig.parameters.keys())
        assert "project" in params
        assert "content" in params
        assert "fact_type" in params
        assert "tags" in params
        assert "source" in params

    def test_adk_search_signature(self):
        """adk_search should accept expected parameters."""
        import inspect

        from cortex.adk.tools import adk_search

        sig = inspect.signature(adk_search)
        params = list(sig.parameters.keys())
        assert "query" in params
        assert "project" in params
        assert "top_k" in params

    def test_adk_status_signature(self):
        """adk_status should accept no parameters."""
        import inspect

        from cortex.adk.tools import adk_status

        sig = inspect.signature(adk_status)
        assert len(sig.parameters) == 0

    def test_adk_ledger_verify_signature(self):
        """adk_ledger_verify should accept no parameters."""
        import inspect

        from cortex.adk.tools import adk_ledger_verify

        sig = inspect.signature(adk_ledger_verify)
        assert len(sig.parameters) == 0

    def test_tools_have_docstrings(self):
        """All ADK tools should have proper docstrings."""
        from cortex.adk.tools import ALL_TOOLS

        for tool in ALL_TOOLS:
            assert tool.__doc__, f"{tool.__name__} missing docstring"
            assert len(tool.__doc__) > 20, f"{tool.__name__} docstring too short"

    def test_tools_return_dict(self):
        """All tools should have dict return type annotation."""
        import inspect

        from cortex.adk.tools import ALL_TOOLS

        for tool in ALL_TOOLS:
            sig = inspect.signature(tool)
            ret = sig.return_annotation
            valid_types = (dict, "dict", "dict[str, Any]")
            assert ret in valid_types or str(ret).startswith("dict[str,"), (
                f"{tool.__name__} should return dict, got {ret}"
            )

    def test_adk_deprecate_signature(self):
        """adk_deprecate should accept expected parameters."""
        import inspect

        from cortex.adk.tools import adk_deprecate

        sig = inspect.signature(adk_deprecate)
        params = list(sig.parameters.keys())
        assert "fact_id" in params
        assert "reason" in params


class TestADKToolRuntime:
    """Exercise the sync runtime path used by ADK tools."""

    class _FakeEngine:
        instances: list["TestADKToolRuntime._FakeEngine"] = []

        def __init__(self, path: str, auto_embed: bool = False) -> None:
            self.path = path
            self.auto_embed = auto_embed
            self.calls: list[tuple[str, tuple, dict]] = []
            type(self).instances.append(self)

        def init_db_sync(self) -> None:
            self.calls.append(("init_db_sync", (), {}))

        def close_sync(self) -> None:
            self.calls.append(("close_sync", (), {}))

        def store_sync(self, *args, **kwargs):
            self.calls.append(("store_sync", args, kwargs))
            return 41

        def search_sync(self, *args, **kwargs):
            self.calls.append(("search_sync", args, kwargs))
            return [
                SimpleNamespace(
                    fact_id=7,
                    score=0.987,
                    project="alpha",
                    fact_type="knowledge",
                    content="alpha result",
                )
            ]

        def stats_sync(self, *args, **kwargs):
            self.calls.append(("stats_sync", args, kwargs))
            return {"active_facts": 3}

        def verify_ledger_sync(self, *args, **kwargs):
            self.calls.append(("verify_ledger_sync", args, kwargs))
            return {"valid": True, "tx_count": 5, "roots_checked": 2, "violations": []}

        def deprecate_sync(self, *args, **kwargs):
            self.calls.append(("deprecate_sync", args, kwargs))
            return True

    def setup_method(self) -> None:
        self._FakeEngine.instances = []

    def test_adk_store_runs_sync_engine_path(self, monkeypatch):
        from cortex.adk import tools as adk_tools

        monkeypatch.setattr(adk_tools, "CortexEngine", self._FakeEngine)

        result = adk_tools.adk_store("alpha", "stored fact", fact_type="decision", tags='["x"]')

        assert result == {"status": "success", "fact_id": 41, "project": "alpha"}
        calls = self._FakeEngine.instances[0].calls
        assert calls[0][0] == "init_db_sync"
        assert calls[1][0] == "store_sync"
        assert calls[-1][0] == "close_sync"

    def test_adk_search_runs_sync_engine_path(self, monkeypatch):
        from cortex.adk import tools as adk_tools

        monkeypatch.setattr(adk_tools, "CortexEngine", self._FakeEngine)

        result = adk_tools.adk_search("alpha", project="proj", top_k=7)

        assert result["status"] == "success"
        assert result["count"] == 1
        assert result["results"][0]["fact_id"] == 7
        assert self._FakeEngine.instances[0].calls[1] == (
            "search_sync",
            (),
            {"query": "alpha", "project": "proj", "top_k": 7},
        )

    def test_adk_status_runs_stats_sync(self, monkeypatch):
        from cortex.adk import tools as adk_tools

        monkeypatch.setattr(adk_tools, "CortexEngine", self._FakeEngine)

        result = adk_tools.adk_status()

        assert result == {"status": "success", "active_facts": 3}
        assert self._FakeEngine.instances[0].calls[1][0] == "stats_sync"

    def test_adk_ledger_verify_accepts_tx_count_shape(self, monkeypatch):
        from cortex.adk import tools as adk_tools

        monkeypatch.setattr(adk_tools, "CortexEngine", self._FakeEngine)

        result = adk_tools.adk_ledger_verify()

        assert result["status"] == "success"
        assert result["transactions_checked"] == 5
        assert result["roots_checked"] == 2
        assert self._FakeEngine.instances[0].calls[1][0] == "verify_ledger_sync"

    def test_adk_deprecate_runs_sync_engine_path(self, monkeypatch):
        from cortex.adk import tools as adk_tools

        monkeypatch.setattr(adk_tools, "CortexEngine", self._FakeEngine)

        result = adk_tools.adk_deprecate(17, reason="stale")

        assert result == {"status": "success", "fact_id": 17, "deprecated": True}
        assert self._FakeEngine.instances[0].calls[1] == (
            "deprecate_sync",
            (17,),
            {"reason": "stale"},
        )


class TestADKAgentCreation:
    """Test agent creation (skip if ADK not installed)."""

    def test_adk_availability_flag(self):
        """is_adk_available should return a bool."""
        from cortex.adk.agents import is_adk_available

        assert isinstance(is_adk_available(), bool)

    def test_create_memory_agent_without_adk(self):
        """If ADK is not installed, create_memory_agent should raise ImportError."""
        from cortex.adk.agents import is_adk_available

        if not is_adk_available():
            with pytest.raises(ImportError, match="google-adk"):
                from cortex.adk.agents import create_memory_agent

                create_memory_agent()
        else:
            pytest.skip("ADK is installed")

    def test_create_analyst_agent_without_adk(self):
        """If ADK is not installed, create_analyst_agent should raise ImportError."""
        from cortex.adk.agents import is_adk_available

        if not is_adk_available():
            with pytest.raises(ImportError, match="google-adk"):
                from cortex.adk.agents import create_analyst_agent

                create_analyst_agent()
        else:
            pytest.skip("ADK is installed")

    def test_create_guardian_agent_without_adk(self):
        """If ADK is not installed, create_guardian_agent should raise ImportError."""
        from cortex.adk.agents import is_adk_available

        if not is_adk_available():
            with pytest.raises(ImportError, match="google-adk"):
                from cortex.adk.agents import create_guardian_agent

                create_guardian_agent()
        else:
            pytest.skip("ADK is installed")

    def test_create_swarm_without_adk(self):
        """If ADK is not installed, create_cortex_swarm should raise ImportError."""
        from cortex.adk.agents import is_adk_available

        if not is_adk_available():
            with pytest.raises(ImportError, match="google-adk"):
                from cortex.adk.agents import create_cortex_swarm

                create_cortex_swarm()
        else:
            pytest.skip("ADK is installed")

    def test_resolve_domain_agents_normalizes_and_deduplicates(self, monkeypatch):
        """Domain agent selection should be deterministic and env-aware."""
        from cortex.adk.agents import resolve_domain_agents

        monkeypatch.setenv("CORTEX_ADK_DOMAIN_AGENTS", "Finance, routing, finance, legal_ops")

        assert resolve_domain_agents() == ["finance", "routing", "legal_ops"]

    def test_resolve_domain_agents_prefers_explicit_values(self, monkeypatch):
        """Explicit domain lists should override environment defaults."""
        from cortex.adk.agents import resolve_domain_agents

        monkeypatch.setenv("CORTEX_ADK_DOMAIN_AGENTS", "ignored, values")

        assert resolve_domain_agents(["Security", "guardrails", "security"]) == [
            "security",
            "guardrails",
        ]

    def test_resolve_domain_agents_uses_default_pack_when_env_missing(self, monkeypatch):
        """Unset domain configuration should fall back to the 230-agent default pack."""
        from cortex.adk.agents import resolve_domain_agents
        from cortex.extensions.adk import agents as adk_agents

        monkeypatch.delenv("CORTEX_ADK_DOMAIN_AGENTS", raising=False)

        resolved = resolve_domain_agents()

        assert resolved == adk_agents._DEFAULT_DOMAIN_AGENTS
        assert len(resolved) == 230
        assert len(set(resolved)) == 230

    def test_resolve_domain_agents_allows_empty_env_override(self, monkeypatch):
        """An explicit empty env value should disable the default specialist pack."""
        from cortex.adk.agents import resolve_domain_agents

        monkeypatch.setenv("CORTEX_ADK_DOMAIN_AGENTS", "")

        assert resolve_domain_agents() == []
