"""SORTU JIT EXECUTOR — Memory-Only AST Evaluation.

Executes ad-hoc code in an isolated namespace for P0 MCTS branch validation.
Axiom Ω4: O(1) Tensor-State Mandate. No disk I/O.
"""

import ast
import logging
import resource
import time

logger = logging.getLogger("CORTEX.SORTU.JIT")


class JITExecutionError(Exception):
    """Raised when JIT code synthesis fails structurally."""


def set_resource_limits() -> None:
    """Limit CPU and memory for sandboxed execution."""
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (1, 1))
        resource.setrlimit(
            resource.RLIMIT_AS,
            (128 * 1024 * 1024, 128 * 1024 * 1024),
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "Could not set resource limits (Mac fallback): %s", e,
        )


def execute_adhoc_synthesis(
    code_str: str,
    entrypoint: str = "resolve_subgraph",
    timeout_ms: int = 50,
) -> dict:
    """Compile and evaluate AST in pure memory, annihilating entropy."""
    start_time = time.perf_counter()

    try:
        tree = ast.parse(code_str, mode="exec")
        compiled_code = compile(tree, filename="<ast_jit>", mode="exec")

        namespace: dict = {
            "__builtins__": {
                "bool": bool, "int": int, "float": float,
                "str": str, "list": list, "dict": dict,
                "set": set, "tuple": tuple, "len": len,
                "sum": sum, "max": max, "min": min, "abs": abs,
                "Exception": Exception, "ValueError": ValueError,
            },
        }

        set_resource_limits()
        exec(compiled_code, namespace)  # noqa: S102

        if entrypoint not in namespace:
            raise JITExecutionError(
                f"Entrypoint '{entrypoint}' not found in JIT code.",
            )

        result = namespace[entrypoint]()
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        if elapsed_ms > timeout_ms:
            logger.error(
                "🛑 [SORTU] Time Limit Exceeded: %.2fms > %dms",
                elapsed_ms, timeout_ms,
            )
            return {
                "status": "TIMEOUT",
                "result": None,
                "elapsed_ms": elapsed_ms,
            }

        logger.info("💎 [SORTU] JIT success in %.2fms", elapsed_ms)
        return {
            "status": "SUCCESS",
            "result": result,
            "elapsed_ms": elapsed_ms,
        }

    except Exception as e:  # noqa: BLE001
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return {
            "status": "ERROR",
            "error": str(e),
            "elapsed_ms": elapsed_ms,
        }
