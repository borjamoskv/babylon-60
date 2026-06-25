with open("cortex/engine/causality/async_graph.py", "r") as f:
    content = f.read()

content = content.replace(
'''        node_states: dict[int, TaintStatus] = {source_id: TaintStatus.TAINTED}
        children_map: dict[int, list[int]] = {}
        for c, ps in edges.items():
            for p in ps: children_map.setdefault(p, []).append(c)
        queue, visited, changes = deque([source_id]), {source_id}, []
        while queue:
            curr_id = queue.popleft()
            data = nodes_data.get(curr_id)
            if not data: continue
            old_conf = data["confidence"]
            new_status = self._derive_node_status(curr_id, source_id, edges, nodes_data, node_states, TaintStatus)
            node_states[curr_id] = new_status
            new_conf = (Confidence.C1.value if floor_to_c1 else _downgrade_confidence(old_conf, 1)) if new_status != TaintStatus.CLEAN else old_conf
            if new_conf != old_conf or new_status != TaintStatus.CLEAN:
                if data["is_json"]: data["metadata"].update({"taint_status": new_status.value, "tainted_by": source_id, "taint_timestamp": timestamp})
                changes.append({"fact_id": curr_id, "old_confidence": old_conf, "new_confidence": new_conf, "status": new_status.value})
            for child_id in children_map.get(curr_id, []):
                if child_id not in visited and child_id in descendant_ids:
                    visited.add(child_id)
                    queue.append(child_id)
        return changes, node_states''',
'''        node_states: dict[int, TaintStatus] = {source_id: TaintStatus.TAINTED}
        children_map: dict[int, list[int]] = {}
        for c, ps in edges.items():
            for p in ps: children_map.setdefault(p, []).append(c)
        queue, visited, changes = deque([source_id]), {source_id}, []
        while queue:
            curr_id = queue.popleft()
            data = nodes_data.get(curr_id)
            if not data: continue
            old_conf = data["confidence"]
            new_status = self._derive_node_status(curr_id, source_id, edges, nodes_data, node_states, TaintStatus)
            node_states[curr_id] = new_status
            new_conf = (Confidence.C1.value if floor_to_c1 else _downgrade_confidence(old_conf, 1)) if new_status != TaintStatus.CLEAN else old_conf
            if new_conf != old_conf or new_status != TaintStatus.CLEAN:
                if data["is_json"]: data["metadata"].update({"taint_status": new_status.value, "tainted_by": source_id, "taint_timestamp": timestamp})
                changes.append({"fact_id": curr_id, "old_confidence": old_conf, "new_confidence": new_conf, "status": new_status.value})
            for child_id in children_map.get(curr_id, []):
                if child_id not in visited and child_id in descendant_ids:
                    visited.add(child_id)
                    queue.append(child_id)
        return changes, node_states'''
)

with open("cortex/engine/causality/async_graph.py", "w") as f:
    f.write(content)
