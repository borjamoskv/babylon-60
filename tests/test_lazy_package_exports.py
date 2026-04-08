from __future__ import annotations

import importlib
import sys


def _reset_package(package_name: str, attrs: tuple[str, ...], submodules: tuple[str, ...]):
    package = importlib.import_module(package_name)
    for attr in attrs:
        package.__dict__.pop(attr, None)
    for submodule in submodules:
        sys.modules.pop(submodule, None)
    return importlib.reload(package)


def test_llm_package_exports_are_lazy() -> None:
    package_name = "cortex.extensions.llm"
    package = _reset_package(
        package_name,
        ("LLMProvider", "LLMManager"),
        (
            "cortex.extensions.llm.provider",
            "cortex.extensions.llm.manager",
        ),
    )

    assert "cortex.extensions.llm.provider" not in sys.modules
    assert "cortex.extensions.llm.manager" not in sys.modules

    provider = package.LLMProvider
    manager = package.LLMManager

    assert provider.__name__ == "LLMProvider"
    assert manager.__name__ == "LLMManager"
    assert "cortex.extensions.llm.provider" in sys.modules
    assert "cortex.extensions.llm.manager" in sys.modules


def test_darknet_package_exports_are_lazy() -> None:
    package_name = "cortex.darknet"
    package = _reset_package(
        package_name,
        ("DarknetAgent", "DarknetIngestor", "DarknetLedger"),
        (
            "cortex.darknet.agents",
            "cortex.darknet.ingestor",
            "cortex.darknet.social_ledger",
        ),
    )

    assert "cortex.darknet.agents" not in sys.modules
    assert "cortex.darknet.ingestor" not in sys.modules
    assert "cortex.darknet.social_ledger" not in sys.modules

    assert package.DarknetAgent.__name__ == "DarknetAgent"
    assert package.DarknetIngestor.__name__ == "DarknetIngestor"
    assert package.DarknetLedger.__name__ == "DarknetLedger"

    assert "cortex.darknet.agents" in sys.modules
    assert "cortex.darknet.ingestor" in sys.modules
    assert "cortex.darknet.social_ledger" in sys.modules


def test_niche_arbitrage_package_exports_are_lazy() -> None:
    package_name = "cortex.extensions.skills.niche_arbitrage"
    package = _reset_package(
        package_name,
        ("MarketReport", "NicheArbitrageEngine", "NicheTarget", "TrendSignal"),
        (
            "cortex.extensions.skills.niche_arbitrage.models",
            "cortex.extensions.skills.niche_arbitrage.pipeline",
        ),
    )

    assert "cortex.extensions.skills.niche_arbitrage.models" not in sys.modules
    assert "cortex.extensions.skills.niche_arbitrage.pipeline" not in sys.modules

    assert package.MarketReport.__name__ == "MarketReport"
    assert package.NicheArbitrageEngine.__name__ == "NicheArbitrageEngine"
    assert package.NicheTarget.__name__ == "NicheTarget"
    assert package.TrendSignal.__name__ == "TrendSignal"

    assert "cortex.extensions.skills.niche_arbitrage.models" in sys.modules
    assert "cortex.extensions.skills.niche_arbitrage.pipeline" in sys.modules


def test_cli_package_exports_console_and_engine_lazily() -> None:
    package_name = "cortex.cli"
    package = _reset_package(
        package_name,
        ("cli", "console", "get_engine"),
        (
            "cortex.cli.main",
            "cortex.cli.common",
        ),
    )

    assert "cortex.cli.main" not in sys.modules
    assert "cortex.cli.common" not in sys.modules

    console = package.console
    get_engine = package.get_engine

    assert console.__class__.__name__ == "Console"
    assert callable(get_engine)
    assert "cortex.cli.common" in sys.modules
