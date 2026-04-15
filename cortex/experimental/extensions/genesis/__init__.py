"""CORTEX Genesis — A System That Creates Systems.

Public API for the Genesis module. Import the engine,
specs, and templates from here.

Example::

    from cortex.experimental.extensions.genesis import GenesisEngine, SystemSpec, ComponentSpec

    engine = GenesisEngine()
    spec = SystemSpec(name="my_module", components=[
        ComponentSpec(name="core", component_type="module"),
    ])
    result = engine.create(spec)
"""

from __future__ import annotations

__all__ = [
    "ComponentSpec",
    "GenesisEngine",
    "GenesisResult",
    "GenesisValidator",
    "SystemAssembler",
    "SystemSpec",
    "SystemTemplate",
    "TemplateRegistry",
]


def __getattr__(name: str) -> object:
    """Lazy imports for all public symbols."""
    if name in ("SystemSpec", "ComponentSpec", "GenesisResult"):
        from cortex.experimental.extensions.genesis.models import ComponentSpec, GenesisResult, SystemSpec

        _map = {
            "SystemSpec": SystemSpec,
            "ComponentSpec": ComponentSpec,
            "GenesisResult": GenesisResult,
        }
        return _map[name]

    if name == "GenesisEngine":
        from cortex.experimental.extensions.genesis.engine import GenesisEngine

        return GenesisEngine

    if name in ("TemplateRegistry", "SystemTemplate"):
        from cortex.experimental.extensions.genesis.templates import SystemTemplate, TemplateRegistry

        _map = {"TemplateRegistry": TemplateRegistry, "SystemTemplate": SystemTemplate}
        return _map[name]

    if name == "SystemAssembler":
        from cortex.experimental.extensions.genesis.assembler import SystemAssembler

        return SystemAssembler

    if name == "GenesisValidator":
        from cortex.experimental.extensions.genesis.validator import GenesisValidator

        return GenesisValidator

    msg = f"module 'cortex.experimental.extensions.genesis' has no attribute {name!r}"
    raise AttributeError(msg)
