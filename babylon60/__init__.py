import sys
import types
import importlib.abc
import importlib.util
import cortex

class ProxyModule(types.ModuleType):
    def __init__(self, name, real_module):
        super().__init__(name)
        object.__setattr__(self, '_real_module', real_module)

    def __getattribute__(self, name):
        if name in ('_real_module', '__class__', '__spec__', '__loader__', '__path__', '__file__', '__name__'):
            return object.__getattribute__(self, name)
        
        # Check if the attribute is a bound submodule on this proxy module
        try:
            val = object.__getattribute__(self, name)
            if isinstance(val, types.ModuleType):
                return val
        except AttributeError:
            pass

        if name == '__dict__':
            try:
                real = object.__getattribute__(self, '_real_module')
            except AttributeError:
                return object.__getattribute__(self, '__dict__')
            d = dict(real.__dict__)
            d.update({
                '__name__': object.__getattribute__(self, '__name__'),
            })
            try:
                d['__spec__'] = object.__getattribute__(self, '__spec__')
            except AttributeError:
                pass
            try:
                d['__loader__'] = object.__getattribute__(self, '__loader__')
            except AttributeError:
                pass
            if hasattr(self, '__path__'):
                d['__path__'] = object.__getattribute__(self, '__path__')
            if hasattr(self, '__file__'):
                d['__file__'] = object.__getattribute__(self, '__file__')
            return d

        return getattr(self._real_module, name)

    def __setattr__(self, name, value):
        if name in ('_real_module', '__spec__', '__loader__', '__path__', '__file__', '__name__'):
            object.__setattr__(self, name, value)
        elif isinstance(value, types.ModuleType):
            object.__setattr__(self, name, value)
        else:
            setattr(self._real_module, name, value)

    def __dir__(self):
        return dir(self._real_module)

class AliasFinder(importlib.abc.MetaPathFinder):
    def __init__(self, alias_name, real_name):
        self.alias_name = alias_name
        self.real_name = real_name
        self._guard = False

    def find_spec(self, fullname, path, target=None):
        if self._guard:
            return None

        if fullname == self.alias_name or fullname.startswith(self.alias_name + '.'):
            # Check if the module actually exists physically under babylon60/
            # (e.g. if we have already migrated it in Wave 2)
            self._guard = True
            try:
                # We temporarily disable our finder to let standard path finders search disk
                spec = importlib.util.find_spec(fullname)
                if spec is not None:
                    # Real module exists on disk under babylon60. Do not alias it.
                    return None
            except Exception:
                pass
            finally:
                self._guard = False

            # If no physical module exists under babylon60, route to cortex
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
        real_module = importlib.import_module(real_module_name)
        
        proxy = ProxyModule(spec.name, real_module)
        if hasattr(real_module, '__path__'):
            proxy.__path__ = real_module.__path__
        if hasattr(real_module, '__file__'):
            proxy.__file__ = real_module.__file__
            
        return proxy

    def exec_module(self, module):
        pass

# Install the proxy in sys.meta_path so that all submodules of babylon60
# resolve to cortex's submodules without executing code twice.
# We ensure it's not added multiple times if reloaded.
if not any(isinstance(f, AliasFinder) and f.alias_name == 'babylon60' for f in sys.meta_path):
    sys.meta_path.insert(0, AliasFinder('babylon60', 'cortex'))

# Create the root proxy module and register it in sys.modules
babylon_root = ProxyModule('babylon60', cortex)
if hasattr(cortex, '__path__'):
    babylon_root.__path__ = cortex.__path__
if hasattr(cortex, '__file__'):
    babylon_root.__file__ = cortex.__file__

sys.modules['babylon60'] = babylon_root
