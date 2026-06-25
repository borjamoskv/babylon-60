"""
Tests for Ouroboros L6: Autopoietic AST Recompilation Engine.
"""

import os
import sys

import pytest

from cortex.engine.autopoiesis.ast_healer import ASTHealer

DUMMY_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "dummy_workspace"))
DUMMY_MODULE_PATH = os.path.join(DUMMY_DIR, "dummy_target.py")
DUMMY_TEST_PATH = os.path.join(DUMMY_DIR, "test_dummy_target.py")

@pytest.fixture
def setup_dummy_module():
    os.makedirs(DUMMY_DIR, exist_ok=True)
    
    # Write the target module
    with open(DUMMY_MODULE_PATH, "w", encoding="utf-8") as f:
        f.write("def calculate_exergy(x: int) -> float:\n    return 10.0 / x\n")
        
    # Write the test for the sandbox to run
    with open(DUMMY_TEST_PATH, "w", encoding="utf-8") as f:
        f.write("from dummy_target import calculate_exergy\ndef test_calculate_exergy():\n    assert calculate_exergy(0) == 0.0\n")
        
    # Add to sys.path and import
    if DUMMY_DIR not in sys.path:
        sys.path.insert(0, DUMMY_DIR)
        
    if "dummy_target" in sys.modules:
        del sys.modules["dummy_target"]
        
    import dummy_target
    yield dummy_target
    
    # Cleanup
    if os.path.exists(DUMMY_MODULE_PATH):
        os.remove(DUMMY_MODULE_PATH)
    if os.path.exists(DUMMY_TEST_PATH):
        os.remove(DUMMY_TEST_PATH)
    if os.path.exists(DUMMY_DIR):
        try:
            os.rmdir(DUMMY_DIR)
        except OSError:
            pass

def test_autopoietic_healing_flow(setup_dummy_module):
    dummy_target = setup_dummy_module
    
    # Initially it fails
    with pytest.raises(ZeroDivisionError):
        dummy_target.calculate_exergy(0)
        
    # We provide the patch
    patch = "try:\n    return 10.0 / x\nexcept ZeroDivisionError:\n    return 0.0"
    
    # Trigger healing
    success = ASTHealer.heal_exception(
        exc=ZeroDivisionError(),
        module_name="dummy_target",
        function_name="calculate_exergy",
        patch_code=patch,
        test_path=DUMMY_TEST_PATH
    )
    
    assert success is True, "Autopoietic healing should return True"
    
    # Now it should work in the live process!
    result = dummy_target.calculate_exergy(0)
    assert result == 0.0
