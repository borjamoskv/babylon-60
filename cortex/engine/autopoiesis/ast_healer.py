"""
C5-REAL AST Healer.
The cognitive core of Ouroboros L6: Parses, patches, and delegates hot-swaps.
"""

from __future__ import annotations

import ast
import logging
import re
import sys

from cortex.engine.autopoiesis.hot_swap import HotSwapper
from cortex.engine.autopoiesis.sandbox import SandboxValidator

logger = logging.getLogger(__name__)

class ASTHealer:
    """Detects exceptions and self-heals by modifying AST."""

    @staticmethod
    def heal_exception(exc: Exception, module_name: str, function_name: str, patch_code: str, test_path: str | None = None) -> bool:
        """
        Attempts to heal the function that threw `exc`.
        `patch_code` should be a valid block of python code.
        """
        logger.warning("Initiating Autopoietic Healing Protocol for %s.%s", module_name, function_name)
        
        if module_name not in sys.modules:
            logger.error("Module %s not in sys.modules", module_name)
            return False
            
        module = sys.modules[module_name]
        file_path = getattr(module, "__file__", None)
        
        if not file_path:
            logger.error("No file path for module %s", module_name)
            return False
            
        # Parse AST
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
            
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            logger.error("Original source has syntax errors: %s", e)
            return False
        
        target_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                target_node = node
                break
                
        if not target_node:
            logger.error("Function %s not found in AST of %s", function_name, file_path)
            return False
            
        # Simplified replacement
        func_pattern = re.compile(rf"(def\s+{function_name}\s*\(.*?\)(\s*->\s*.*?)?:)([\s\S]*?)(?=\n\S|\Z)", re.MULTILINE)
        
        match = func_pattern.search(source)
        if not match:
            logger.error("Could not match function signature with regex")
            return False
            
        new_func_def = match.group(1)
        indented_patch = "\n".join(f"    {line}" for line in patch_code.strip().split("\n"))
        
        new_source = source[:match.start()] + new_func_def + "\n" + indented_patch + "\n" + source[match.end():]
        
        # Write back to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_source)
            
        # Sandbox Validation
        try:
            seal = SandboxValidator.validate_patch(file_path, test_path)
        except RuntimeError as e:
            logger.error("Sandbox validation rejected patch: %s", e)
            # Rollback
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(source)
            return False
            
        # Hot Swap
        try:
            success = HotSwapper.apply_patch(module_name, function_name, seal)
            return success
        except Exception as e:
            logger.error("Hot Swap failed: %s", e)
            # Rollback
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(source)
            return False
