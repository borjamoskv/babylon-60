# [C5-REAL] Exergy-Maximized
"""Helpers for SICA self-healing Reflexion loop."""

from __future__ import annotations

from cortex.isa.builder import (
    AgentOp,
    dispatch_targets,
    node_count,
)


class DiagnosisStrategy:
    """Rule-based diagnosis engine. Analyzes errors to produce structured
    reflections without requiring LLM inference (deterministic, O(1)).
    """

    # Common error patterns → structured diagnoses
    _PATTERNS: list[tuple[str, str, str]] = [
        # (error_substring, diagnosis, proposed_fix)
        (
            "timeout",
            "Dispatch target exceeded time budget. Likely I/O bound or deadlocked.",
            "Add timeout guard to dispatch node or reduce payload size.",
        ),
        (
            "connection",
            "Network or database connection failure. Transient infrastructure error.",
            "Wrap dispatch in retry-with-backoff. Consider circuit breaker.",
        ),
        (
            "permission",
            "Insufficient permissions for the requested operation.",
            "Verify capability guard allows this target. Escalate if needed.",
        ),
        (
            "not found",
            "Dispatch target or resource does not exist.",
            "Validate target exists before dispatch. Add fallback branch.",
        ),
        (
            "rate limit",
            "External API rate limit hit. Too many requests in window.",
            "Add throttle node before dispatch. Implement exponential backoff.",
        ),
        (
            "memory",
            "Memory allocation failure. Payload too large or leak detected.",
            "Reduce batch size. Add memory guard to pipeline.",
        ),
        (
            "assertion",
            "Internal invariant violated. Logic error in dispatch tree.",
            "Review tree structure. Check predicate conditions in Cond nodes.",
        ),
        (
            "serialization",
            "Failed to serialize/deserialize payload across FFI boundary.",
            "Validate payload is JSON-serializable before crossing to Rust.",
        ),
    ]

    @classmethod
    def diagnose(cls, error: Exception, tree: AgentOp) -> tuple[str, str]:
        """Returns (diagnosis, proposed_fix) for the given error and tree context."""
        error_lower = str(error).lower()
        error_type = type(error).__name__.lower()

        for pattern, diagnosis, fix in cls._PATTERNS:
            if pattern in error_lower or pattern in error_type:
                # Enrich with tree context
                targets = dispatch_targets(tree)
                nodes = node_count(tree)
                enriched_diagnosis = f"{diagnosis} [tree: {nodes} nodes, targets: {targets}]"
                return enriched_diagnosis, fix

        # Fallback: generic diagnosis with full context
        targets = dispatch_targets(tree)
        return (
            f"Unclassified error ({type(error).__name__}): {str(error)[:200]}. "
            f"Tree has {node_count(tree)} nodes targeting {targets}.",
            "Inspect tree structure manually. Consider decomposing into smaller subtrees.",
        )


class TreeRewriter:
    """Applies structural modifications to dispatch trees based on reflections."""

    @staticmethod
    def apply_retry_wrapper(tree: AgentOp, max_retries: int = 2) -> AgentOp:
        """Wrap all Dispatch nodes in retry logic."""
        if isinstance(tree, str):
            return tree
        if not isinstance(tree, dict):
            return tree

        result = {}
        for variant, data in tree.items():
            if variant == "Dispatch" and isinstance(data, dict):
                # Wrap dispatch in a loop for retry
                result = {
                    "Loop": {
                        "count": max_retries,
                        "body": {variant: data},
                    }
                }
            elif variant in ("Seq", "Par") and isinstance(data, list):
                result[variant] = [  # pyright: ignore[reportArgumentType]
                    TreeRewriter.apply_retry_wrapper(child, max_retries) for child in data
                ]
            elif variant == "Cond" and isinstance(data, dict):
                result[variant] = {
                    "predicate": data.get("predicate"),
                    "then_branch": TreeRewriter.apply_retry_wrapper(
                        data.get("then_branch", {}), max_retries
                    ),
                    "else_branch": TreeRewriter.apply_retry_wrapper(
                        data.get("else_branch", "Noop"), max_retries
                    ),
                }
            elif variant == "Loop" and isinstance(data, dict):
                result[variant] = {
                    "count": data.get("count", 1),
                    "body": TreeRewriter.apply_retry_wrapper(data.get("body", {}), max_retries),
                }
            else:
                result[variant] = data

        return result

    @staticmethod
    def add_timeout_guard(tree: AgentOp, timeout_ms: int = 5000) -> AgentOp:
        """Wrap the entire tree in a conditional timeout halt."""
        from cortex.isa.builder import Predicate, cond, halt, seq

        return seq(
            tree,
            cond(
                Predicate.always(),
                then_branch=halt(success=True),
                else_branch=halt(timeout_ms=timeout_ms),
            ),
        )

    @staticmethod
    def remove_failed_target(tree: AgentOp, target: str) -> AgentOp:
        """Remove a specific dispatch target from the tree."""
        if isinstance(tree, str):
            return tree
        if not isinstance(tree, dict):
            return tree

        result = {}
        for variant, data in tree.items():
            if variant == "Dispatch" and isinstance(data, dict):
                if data.get("target") == target:
                    return "Noop"  # Replace failed target with noop  # pyright: ignore[reportReturnType]
                result[variant] = data
            elif variant in ("Seq", "Par") and isinstance(data, list):
                children = [TreeRewriter.remove_failed_target(child, target) for child in data]
                # Filter out Noops from parallel branches
                if variant == "Par":
                    children = [c for c in children if c != "Noop"]
                result[variant] = children
            elif variant == "Cond" and isinstance(data, dict):
                result[variant] = {
                    "predicate": data.get("predicate"),
                    "then_branch": TreeRewriter.remove_failed_target(
                        data.get("then_branch", {}), target
                    ),
                    "else_branch": TreeRewriter.remove_failed_target(
                        data.get("else_branch", "Noop"), target
                    ),
                }
            else:
                result[variant] = data

        return result
