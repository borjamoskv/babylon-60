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
    def apply_patch(module_name: str, function_name: str, seal: C5Seal) -> bool:
        """
        Hot-swaps a function's code object in the live RAM.
        Requires a valid C5Seal.
        """
        if not seal:
            raise ValueError("Cannot hot-swap without a valid C5Seal")

        logger.info("Applying Hot-Swap to %s.%s (Seal: %s)", module_name, function_name, seal.ast_hash[:8])

        if module_name not in sys.modules:
            raise ImportError(f"Module {module_name} is not loaded in RAM")

        module = sys.modules[module_name]
        
        try:
            target_func = getattr(module, function_name)
            if not isinstance(target_func, types.FunctionType):
                raise TypeError(f"Target {function_name} is not a FunctionType")
                
            # Read and compile the file
            file_path = module.__file__
            if not file_path:
                raise RuntimeError(f"Cannot resolve file path for {module_name}")
                
            with open(file_path, encoding="utf-8") as f:
                source = f.read()
                
            # Compile into code object
            compiled = compile(source, file_path, "exec")
            
            # Find the function's code object within the compiled module
            new_code = None
            for const in compiled.co_consts:
                if isinstance(const, types.CodeType) and const.co_name == function_name:
                    new_code = const
                    break
                    
            if not new_code:
                raise RuntimeError(f"Could not find compiled code for {function_name}")
                
            # Perform the hot-swap mutation
            target_func.__code__ = new_code
            logger.info("Hot-Swap SUCCESS. Function %s mutated in RAM.", function_name)
            return True
            
        except Exception as e:
            logger.error("Hot-Swap FAILED: %s", e)
            raise RuntimeError(f"Hot-Swap Entropy: {e}") from e
