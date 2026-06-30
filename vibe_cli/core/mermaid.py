def generate_mermaid(dependency_graph: dict, max_nodes: int = 30):
    lines = ["graph TD"]

    nodes = list(dependency_graph.keys())[:max_nodes]

    for file in nodes:
        imports = dependency_graph.get(file, [])
        src = file.replace("/", "_").replace(".", "_").replace("-", "_")

        if not imports:
            lines.append(f"    {src}")
            continue

        for imp in imports[:5]:
            dst = imp.replace("/", "_").replace(".", "_").replace("-", "_")
            lines.append(f"    {src} --> {dst}")

    return "\n".join(lines)
