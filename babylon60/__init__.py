import sys
import importlib.abc
import importlib.util
import cortex

class AliasFinder(importlib.abc.MetaPathFinder):
    def __init__(self, alias_name, real_name):
        self.alias_name = alias_name
        self.real_name = real_name

    def find_spec(self, fullname, path, target=None):
        if fullname == self.alias_name or fullname.startswith(self.alias_name + '.'):
            real_module_name = fullname.replace(self.alias_name, self.real_name, 1)
            try:
                spec = importlib.util.find_spec(real_module_name)
                if spec is None:
                    return None
            except ModuleNotFoundError:
                return None

            alias_spec = importlib.util.spec_from_loader(
                fullname,
                AliasLoader(self.alias_name, self.real_name)
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
# We ensure it's not added multiple times if reloaded.
if not any(isinstance(f, AliasFinder) and f.alias_name == 'babylon60' for f in sys.meta_path):
    sys.meta_path.insert(0, AliasFinder('babylon60', 'cortex'))

# Finally, overwrite this very module in sys.modules with the cortex module
# so that `import babylon60` resolves directly to the cortex module object.
sys.modules['babylon60'] = cortex
