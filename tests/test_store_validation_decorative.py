"""Tests for store_validation decorative mode tuple unpacking.

Verifies that should_enter_decorative_mode's tuple return is correctly
unpacked — preventing the false-positive DECORATIVE mode entry bug.
"""

from __future__ import annotations

from decimal import Decimal

from cortex.guards.thermodynamic import ThermodynamicCounters


class TestDecorativeModeUnpacking:
    def test_false_tuple_does_not_trigger_decorative(self):
        """(False, []) must NOT trigger decorative mode.

        Before the fix, the raw tuple was truthy, so the agent always
        entered DECORATIVE mode even when counters were healthy.
        """
        counters = ThermodynamicCounters(
            file_reads_without_ast_delta=0,
            context_expansion_rate=Decimal("0.1"),
            uncertainty_reduction_rate=Decimal("0.9"),
        )
        from cortex.guards.thermodynamic import should_enter_decorative_mode

        triggered, reasons = should_enter_decorative_mode(counters)
        assert triggered is False, "Healthy counters must NOT trigger decorative mode"
        assert reasons == []

    def test_true_tuple_triggers_decorative(self):
        """(True, [...]) must trigger decorative mode."""
        counters = ThermodynamicCounters(
            file_reads_without_ast_delta=6,
        )
        from cortex.guards.thermodynamic import should_enter_decorative_mode

        triggered, reasons = should_enter_decorative_mode(counters)
        assert triggered is True
        assert len(reasons) > 0
