from __future__ import annotations

import importlib
import sys
import warnings


def _reload_extensions_adk_tools():
    sys.modules.pop("cortex.extensions.adk.tools", None)
    return importlib.import_module("cortex.extensions.adk.tools")


def test_extensions_adk_tools_reexports_canonical_symbols() -> None:
    from cortex.adk import tools as canonical_tools

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        shim_tools = _reload_extensions_adk_tools()

    assert any(item.category is DeprecationWarning for item in caught)
    assert shim_tools.__all__ == canonical_tools.__all__
    for name in canonical_tools.__all__:
        assert getattr(shim_tools, name) is getattr(canonical_tools, name)


def test_extensions_adk_all_tools_matches_canonical_registry() -> None:
    from cortex.adk import tools as canonical_tools

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        shim_tools = _reload_extensions_adk_tools()

    assert shim_tools.ALL_TOOLS == canonical_tools.ALL_TOOLS
