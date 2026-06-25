import sys
import os

# Append paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../sdk/babylon60-mtk/src')))

from babylon60_mtk import install_bootstrap_watchdog
from babylon60_mtk.watchdog import _is_mitosis_branch

def run_tests():
    print("[TEST] Instalando MTK Bootstrap Watchdog...")
    install_bootstrap_watchdog()
    
    # 1. Test read operation (should always pass)
    try:
        with open("babylon60/nodes/causal_framework_nodes.py", "r") as f:
            pass
        print("[OK] Leer archivos del core está permitido.")
    except PermissionError:
        print("[FAIL] Lectura bloqueada incorrectamente.")
        sys.exit(1)
        
    # 2. Check current branch state
    is_mitosis = _is_mitosis_branch()
    print(f"[TEST] Estamos en rama de mitosis? {is_mitosis}")
    
    # 3. Test write operation
    test_file = "babylon60/test_watchdog_file.txt"
    if is_mitosis:
        try:
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            print("[OK] Escritura permitida porque estamos en una rama de mitosis.")
        except PermissionError as e:
            print(f"[FAIL] Escritura bloqueada incorrectamente estando en mitosis. Error: {e}")
            sys.exit(1)
    else:
        try:
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            print("[FAIL] Escritura permitida sin estar en mitosis. Watchdog falló.")
            sys.exit(1)
        except PermissionError as e:
            print(f"[OK] Escritura bloqueada correctamente: {e}")
            
    print("[SUCCESS] Bootstrap Watchdog funcionando de acuerdo a LEY 10 (Autopoiesis).")

if __name__ == "__main__":
    run_tests()
