class PlannerAgent:
    def run(self, state):
        for debt in state.technical_debt:
            state.tasks.append({
                "id": f"T-{len(state.tasks)+1:03d}",
                "title": f"Resolve TODO in {debt['file']}",
                "priority": "medium",
                "type": "debt"
            })

        if state.stack.get("python") and state.stack.get("node"):
            state.tasks.append({
                "id": f"T-{len(state.tasks)+1:03d}",
                "title": "Document frontend-backend integration",
                "priority": "high",
                "type": "documentation"
            })

        if len(state.conflicts) > 0:
            state.tasks.append({
                "id": f"T-{len(state.tasks)+1:03d}",
                "title": "Resolve architectural conflicts",
                "priority": "high",
                "type": "architecture"
            })

        state.tasks.append({
            "id": f"T-{len(state.tasks)+1:03d}",
            "title": "Generate clean canonical README",
            "priority": "high",
            "type": "documentation"
        })

        state.tasks.append({
            "id": f"T-{len(state.tasks)+1:03d}",
            "title": "Review dependency graph for cycles",
            "priority": "medium",
            "type": "architecture"
        })

        return state
