from __future__ import annotations

from typing import Any


class TaintStatusMixin:
    """Provides status resolution methods for the taint propagation process."""

    def _derive_node_status(
        self,
        curr_id: int,
        source_id: int,
        edges: dict[int, list[int]],
        nodes_data: dict[int, dict[str, Any]],
        node_states: dict[int, Any],
        TaintStatus: Any,
    ) -> Any:
        if curr_id == source_id:
            return TaintStatus.TAINTED

        parents = edges.get(curr_id, [])
        if not parents:
            return TaintStatus.CLEAN

        p_states = []
        for pid in parents:
            if pid in node_states:
                p_states.append(node_states[pid])
            else:
                p_meta = nodes_data.get(pid, {}).get("metadata", {})
                p_status = p_meta.get("taint_status", TaintStatus.CLEAN.value)
                p_states.append(
                    TaintStatus(p_status)
                    if p_status in TaintStatus._value2member_map_
                    else TaintStatus.CLEAN
                )

        if all(s == TaintStatus.TAINTED for s in p_states):
            return TaintStatus.TAINTED
        if any(s in (TaintStatus.TAINTED, TaintStatus.SUSPECT) for s in p_states):
            return TaintStatus.SUSPECT
        return TaintStatus.CLEAN
