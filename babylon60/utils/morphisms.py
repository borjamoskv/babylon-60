# [C5-REAL] Exergy-Maximized
"""
Sovereign Morphisms and Algebraic Invariant Verification Module.

Enforces structural sanity across CORTEX state transformations using
formal algebraic checks (Homomorphisms, Isomorphisms, Endomorphisms, etc.).

SYS_ID: borjamoskv
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any


class MorphismVerifier:
    """
    Formal validator for mathematical morphisms and algebraic properties of
    system functions and state transformations.
    """

    @staticmethod
    def is_homomorphism(
        f: Callable[[Any], Any],
        op_in: Callable[[Any, Any], Any],
        op_out: Callable[[Any, Any], Any],
        domain_sample: Sequence[tuple[Any, Any]],
        tol: float = 1e-9,
    ) -> bool:
        """
        Verifies if f is a homomorphism: f(a op_in b) == f(a) op_out f(b).

        Returns True if the property holds for all pairs in the domain_sample.
        """
        for a, b in domain_sample:
            try:
                lhs = f(op_in(a, b))
                rhs = op_out(f(a), f(b))

                # Handle numeric close checking
                if isinstance(lhs, (float, int)) and isinstance(rhs, (float, int)):
                    if abs(lhs - rhs) > tol:
                        return False
                # Handle Dual numbers or objects with val/der properties
                elif hasattr(lhs, "val") and hasattr(rhs, "val"):
                    if abs(lhs.val - rhs.val) > tol or abs(lhs.der - rhs.der) > tol:
                        return False
                else:
                    if lhs != rhs:
                        return False
            except (ValueError, TypeError, ZeroDivisionError, AttributeError):
                return False
        return True

    @staticmethod
    def is_isomorphism(
        f: Callable[[Any], Any],
        f_inv: Callable[[Any], Any],
        domain_sample: Sequence[Any],
        tol: float = 1e-9,
    ) -> bool:
        """
        Verifies if f and f_inv form a structural isomorphism (bijection).
        Checks the round-trip identities:
        1. f_inv(f(x)) == x
        2. f(f_inv(y)) == y (implied by applying to mapped elements)
        """
        for x in domain_sample:
            try:
                # Round-trip check: x -> f(x) -> f_inv(f(x)) -> should be close to x
                mapped = f(x)
                recovered = f_inv(mapped)

                if isinstance(x, (float, int)) and isinstance(recovered, (float, int)):
                    if abs(recovered - x) > tol:
                        return False
                elif hasattr(x, "val") and hasattr(recovered, "val"):
                    if abs(recovered.val - x.val) > tol or abs(recovered.der - x.der) > tol:
                        return False
                else:
                    if recovered != x:
                        return False
            except (ValueError, TypeError, ZeroDivisionError, AttributeError):
                return False
        return True

    @staticmethod
    def is_endomorphism(
        f: Callable[[Any], Any],
        domain_sample: Sequence[Any],
        domain_guard: Callable[[Any], bool],
    ) -> bool:
        """
        Verifies if f is an endomorphism: Domain(f) == Codomain(f).
        Checks if f(x) belongs to the same domain as x.
        """
        for x in domain_sample:
            try:
                if not domain_guard(x):
                    return False
                result = f(x)
                if not domain_guard(result):
                    return False
            except (ValueError, TypeError, AttributeError):
                return False
        return True

    @staticmethod
    def is_automorphism(
        f: Callable[[Any], Any],
        f_inv: Callable[[Any], Any],
        domain_sample: Sequence[Any],
        domain_guard: Callable[[Any], bool],
        tol: float = 1e-9,
    ) -> bool:
        """
        Verifies if f is an automorphism: an endomorphism that is also an isomorphism.
        """
        if not MorphismVerifier.is_endomorphism(f, domain_sample, domain_guard):
            return False
        return MorphismVerifier.is_isomorphism(f, f_inv, domain_sample, tol)

    @staticmethod
    def is_idempotent(
        f: Callable[[Any], Any],
        domain_sample: Sequence[Any],
        tol: float = 1e-9,
    ) -> bool:
        """
        Verifies if f is idempotent: f(f(x)) == f(x).
        Commonly holds for projectors.
        """
        for x in domain_sample:
            try:
                fx = f(x)
                ffx = f(fx)

                if isinstance(fx, (float, int)) and isinstance(ffx, (float, int)):
                    if abs(ffx - fx) > tol:
                        return False
                elif hasattr(fx, "val") and hasattr(ffx, "val"):
                    if abs(ffx.val - fx.val) > tol or abs(ffx.der - fx.der) > tol:
                        return False
                else:
                    if ffx != fx:
                        return False
            except (ValueError, TypeError, ZeroDivisionError, AttributeError):
                return False
        return True

    @staticmethod
    def is_involution(
        f: Callable[[Any], Any],
        domain_sample: Sequence[Any],
        tol: float = 1e-9,
    ) -> bool:
        """
        Verifies if f is an involution: f(f(x)) == x.
        Commonly holds for reflections and dualities.
        """
        for x in domain_sample:
            try:
                ffx = f(f(x))

                if isinstance(x, (float, int)) and isinstance(ffx, (float, int)):
                    if abs(ffx - x) > tol:
                        return False
                elif hasattr(x, "val") and hasattr(ffx, "val"):
                    if abs(ffx.val - x.val) > tol or abs(ffx.der - x.der) > tol:
                        return False
                else:
                    if ffx != x:
                        return False
            except (ValueError, TypeError, ZeroDivisionError, AttributeError):
                return False
        return True
