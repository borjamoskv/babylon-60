import os
import importlib.util
import sys

def import_file(filepath):
    module_name = filepath.replace('/', '.').replace('\\', '.').replace('.py', '')
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    if not spec or not spec.loader: return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
        return True
    except Exception as e:
        print(f"FAILED: {filepath} -> {e}")
        return False

for root, dirs, files in os.walk('tests'):
    for f in sorted(files):
        if f.startswith('test_') and f.endswith('.py'):
            filepath = os.path.join(root, f)
            import_file(filepath)
