import sys
import pytest
import asyncio
from cortex.engine.autopoiesis.ast_healer import ASTHealer

@pytest.fixture
def dummy_module(tmp_path):
    """Creates a temporary module for testing AST modifications."""
    mod_name = "dummy_healer_module"
    mod_path = tmp_path / f"{mod_name}.py"
    
    code = """
class MyTargetClass:
    def buggy_method(self) -> int:
        raise ValueError("I am broken")
        
    async def async_buggy_method(self) -> int:
        raise ValueError("I am broken too")

def buggy_function() -> str:
    raise RuntimeError("Function is broken")
"""
    mod_path.write_text(code, encoding="utf-8")
    
    # Add to sys.path and import
    sys.path.insert(0, str(tmp_path))
    import dummy_healer_module
    
    yield dummy_healer_module, str(mod_path)
    
    # Cleanup
    sys.path.remove(str(tmp_path))
    if mod_name in sys.modules:
        del sys.modules[mod_name]

def test_heal_top_level_function(dummy_module):
    mod, mod_path = dummy_module
    
    # Verify it is broken
    with pytest.raises(RuntimeError):
        mod.buggy_function()
        
    patch_code = '''
def buggy_function() -> str:
    return "I am fixed!"
'''
    
    # We pass test_path to avoid the validator running the whole cortex-persist test suite
    success = ASTHealer.heal_exception(
        exc=RuntimeError("Function is broken"),
        module_name=mod.__name__,
        function_name="buggy_function",
        patch_code=patch_code,
        class_name=None,
        test_path=mod_path  # A module isn't a test, but the SandboxValidator runs pytest against it. It will pass since there are no test failures.
    )
    
    assert success is True
    
    # Now it should be fixed in RAM!
    assert mod.buggy_function() == "I am fixed!"


def test_heal_class_method(dummy_module):
    mod, mod_path = dummy_module
    instance = mod.MyTargetClass()
    
    with pytest.raises(ValueError):
        instance.buggy_method()
        
    patch_code = '''
def buggy_method(self) -> int:
    return 42
'''
    
    success = ASTHealer.heal_exception(
        exc=ValueError("I am broken"),
        module_name=mod.__name__,
        function_name="buggy_method",
        patch_code=patch_code,
        class_name="MyTargetClass",
        test_path=mod_path
    )
    
    assert success is True
    assert instance.buggy_method() == 42


@pytest.mark.asyncio
async def test_heal_async_class_method(dummy_module):
    mod, mod_path = dummy_module
    instance = mod.MyTargetClass()
    
    with pytest.raises(ValueError):
        await instance.async_buggy_method()
        
    patch_code = '''
async def async_buggy_method(self) -> int:
    return 100
'''
    
    success = ASTHealer.heal_exception(
        exc=ValueError("I am broken too"),
        module_name=mod.__name__,
        function_name="async_buggy_method",
        patch_code=patch_code,
        class_name="MyTargetClass",
        test_path=mod_path
    )
    
    assert success is True
    assert await instance.async_buggy_method() == 100

def test_sandbox_rejection(dummy_module):
    mod, mod_path = dummy_module
    
    patch_code = '''
def buggy_function() -> str:
    syntax_error__ = 
'''
    
    success = ASTHealer.heal_exception(
        exc=RuntimeError("Function is broken"),
        module_name=mod.__name__,
        function_name="buggy_function",
        patch_code=patch_code,
        class_name=None,
        test_path=mod_path
    )
    
    assert success is False
    
    # Verify it is still broken
    with pytest.raises(RuntimeError):
        mod.buggy_function()
