# [C5-REAL] Exergy-Maximized
"""
Strangler Fig compatibility layer for BABYLON-60.
Ensures that all submodules of babylon60 resolve to cortex's submodules
unless a physical module has been introduced under the babylon60 namespace.
"""

import sys
import os
import importlib.abc
import importlib.util
from pathlib import Path

# Helper to check if a module physically exists under babylon60 directory
def _has_physical_module(fullname: str) -> bool:
    project_root = Path(__file__).resolve().parent.parent
    parts = fullname.split(".")
    if fullname == "babylon60":
        return (project_root / "babylon60" / "__init__.py").exists()
    subpath = Path(*parts)
    py_file = project_root / f"{subpath}.py"
    init_file = project_root / subpath / "__init__.py"
    return py_file.exists() or init_file.exists()

class AliasFinder(importlib.abc.MetaPathFinder):
    def __init__(self, alias_name, real_name):
        self.alias_name = alias_name
        self.real_name = real_name

    def find_spec(self, fullname, path, target=None):
        if fullname == self.alias_name or fullname.startswith(self.alias_name + '.'):
            # If a physical replacement module exists in the babylon60 directory,
            # allow standard import machinery to load it.
            if fullname != self.alias_name and _has_physical_module(fullname):
                return None
                
            real_module_name = fullname.replace(self.alias_name, self.real_name, 1)
            try:
                spec = importlib.util.find_spec(real_module_name)
                if spec is None:
                    return None
            except ModuleNotFoundError:
                return None

            alias_spec = importlib.util.spec_from_loader(
                fullname,
                AliasLoader(self.alias_name, self.real_name),
                origin=getattr(spec, "origin", None)
            )
            return alias_spec
        return None

class AliasLoader(importlib.abc.Loader):
    def __init__(self, alias_name, real_name):
        self.alias_name = alias_name
        self.real_name = real_name

    def create_module(self, spec):
        real_module_name = spec.name.replace(self.alias_name, self.real_name, 1)
        __import__(real_module_name)
        return sys.modules[real_module_name]

    def exec_module(self, module):
        pass

# Install the proxy in sys.meta_path so that all submodules of babylon60
# resolve to cortex's submodules without executing code twice.
if not any(isinstance(f, AliasFinder) and f.alias_name == 'babylon60' for f in sys.meta_path):
    sys.meta_path.insert(0, AliasFinder('babylon60', 'cortex'))

# Expose cortex elements on this module dynamically so `import babylon60` behaves
# like a proxy without overwriting the module in sys.modules.
import cortex
def __getattr__(name):
    return getattr(cortex, name)

# Ensure __all__ matches cortex
__all__ = getattr(cortex, "__all__", [])

