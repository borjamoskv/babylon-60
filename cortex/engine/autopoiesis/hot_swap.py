"""
C5-REAL RAM Hot-Swapper.
Replaces function bytecode dynamically without breaking the event loop.
"""

from __future__ import annotations

import logging
import sys
import types

from cortex.engine.autopoiesis.sandbox import C5Seal

logger = logging.getLogger(__name__)

class HotSwapper:
    """Manages dynamic RAM mutation of Python objects."""

    @staticmethod
    def _find_code_object(code: types.CodeType, function_name: str, class_name: str | None = None) -> types.CodeType | None:
        """Recursively searches for a code object by name, respecting class scope if provided."""
        for const in code.co_consts:
            if isinstance(const, types.CodeType):
                if class_name and const.co_name == class_name:
                    # Found the class, now find the function inside it
                    return HotSwapper._find_code_object(const, function_name, None)
                elif not class_name and const.co_name == function_name:
                    return const
                else:
                    # Recursive search
                    found = HotSwapper._find_code_object(const, function_name, class_name)
                    if found:
                        return found
        return None

    @staticmethod
    def apply_patch(module_name: str, function_name: str, seal: C5Seal, class_name: str | None = None) -> bool:
        """
        Hot-swaps a function's code object in the live RAM.
        Requires a valid C5Seal. Supports top-level functions and class methods.
        """
        if not seal:
            raise ValueError("Cannot hot-swap without a valid C5Seal")

        logger.info("Applying Hot-Swap to %s:%s.%s (Seal: %s)", module_name, class_name or "GLOBAL", function_name, seal.ast_hash[:8])

        if module_name not in sys.modules:
            raise ImportError(f"Module {module_name} is not loaded in RAM")

        module = sys.modules[module_name]
        
        try:
            if class_name:
                target_container = getattr(module, class_name)
            else:
                target_container = module
                
            target_func = getattr(target_container, function_name)
            
            # For class methods, we might need to unwrap staticmethod/classmethod
            actual_func = target_func
            if isinstance(target_func, (staticmethod, classmethod)):
                actual_func = target_func.__func__
                
            if not hasattr(actual_func, '__code__'):
                raise TypeError(f"Target {function_name} does not have a __code__ attribute")
                
            # Read and compile the file
            file_path = module.__file__
            if not file_path:
                raise RuntimeError(f"Cannot resolve file path for {module_name}")
                
            with open(file_path, encoding="utf-8") as f:
                source = f.read()
                
            # Compile into code object
            compiled = compile(source, file_path, "exec")
            
            # Find the function's code object within the compiled module
            new_code = HotSwapper._find_code_object(compiled, function_name, class_name)
                    
            if not new_code:
                raise RuntimeError(f"Could not find compiled code for {function_name}")
                
            # Perform the hot-swap mutation
            actual_func.__code__ = new_code
            logger.info("Hot-Swap SUCCESS. Function %s mutated in RAM.", function_name)
            return True
            
        except Exception as e:
            logger.error("Hot-Swap FAILED: %s", e)
            raise RuntimeError(f"Hot-Swap Entropy: {e}") from e
