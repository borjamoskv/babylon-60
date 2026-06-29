# [C5-REAL] Exergy-Maximized
"""
cat_id: dependency-mapper
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""

import ast
import os
from collections import defaultdict

deps_to_find = [
    "sqlite_vec", "aiosqlite", "click", "rich", "pydantic", 
    "langchain", "langchain_core", "langchain_community", "langchain_ollama", 
    "confluent_kafka", "numpy", "fastapi", "starlette", "uvicorn", "httpx", 
    "mcp", "watchdog", "aiohttp", "neo4j", "stripe", "pytrends", "pandas",
    "sentence_transformers", "onnxruntime", "chromadb"
]

mapping = defaultdict(list)

search_dirs = ["cortex", "babylon60", "cortex-system", "moskv-swarm"]

for s_dir in search_dirs:
    if not os.path.exists(s_dir):
        continue
    for root, _, files in os.walk(s_dir):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, encoding="utf-8") as f:
                    content = f.read()
                try:
                    tree = ast.parse(content, filename=path)
                except Exception:
                    continue
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            base = alias.name.split('.')[0]
                            if base in deps_to_find:
                                mapping[base].append(path)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            base = node.module.split('.')[0]
                            if base in deps_to_find:
                                mapping[base].append(path)

out_path = "/Users/borjafernandezangulo/.gemini/antigravity/brain/fb2c8891-3e03-488c-a064-f6387507b5d8/dependency_map.md"
os.makedirs(os.path.dirname(out_path), exist_ok=True)

with open(out_path, "w") as out:
    out.write("# Mapa de Dependencias a Eliminar (UltraThink Blast Radius)\n\n")
    for dep in sorted(deps_to_find):
        files = sorted(list(set(mapping.get(dep, []))))
        out.write(f"### `{dep}` ({len(files)} files)\n")
        if not files:
            out.write("- No usage found via AST imports.\n")
        else:
            for f in files:
                out.write(f"- `{f}`\n")
        out.write("\n")
print(f"Mapping complete. See {out_path}")
