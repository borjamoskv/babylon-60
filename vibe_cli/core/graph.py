def detect_cycles(dependency_graph: dict):
    visited = set()
    rec_stack = set()
    cycles = []

    def dfs(node, path):
        visited.add(node)
        rec_stack.add(node)

        for neighbor in dependency_graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor, path + [neighbor])
            elif neighbor in rec_stack:
                cycle_start = path.index(neighbor) if neighbor in path else 0
                cycles.append(path[cycle_start:] + [neighbor])

        rec_stack.discard(node)

    for node in dependency_graph:
        if node not in visited:
            dfs(node, [node])

    return cycles
