import ast
import os
import sys
import hashlib
from collections import defaultdict

def get_ast_hash(node):
    # Hash an AST node by dumping it without line numbers
    dump = ast.dump(node, annotate_fields=False)
    return hashlib.md5(dump.encode('utf-8')).hexdigest()

def find_duplicates(directory):
    functions_by_hash = defaultdict(list)
    classes_by_hash = defaultdict(list)

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        source = f.read()
                    
                    tree = ast.parse(source, filename=path)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                            # Ignore very short functions (e.g. less than 3 statements)
                            if len(node.body) > 3:
                                h = get_ast_hash(node)
                                functions_by_hash[h].append((path, node.name, node.lineno))
                        elif isinstance(node, ast.ClassDef):
                            if len(node.body) > 3:
                                h = get_ast_hash(node)
                                classes_by_hash[h].append((path, node.name, node.lineno))
                except Exception as e:
                    pass

    return functions_by_hash, classes_by_hash

print("Searching for duplicated functions and classes...")
funcs, classes = find_duplicates("cortex")

print("\n--- Duplicated Functions ---")
for h, locations in funcs.items():
    if len(locations) > 1:
        # Check if they have the same name or structure
        print(f"Duplicate logic found ({len(locations)} occurrences):")
        for loc in locations:
            print(f"  - {loc[0]} : {loc[1]} (Line {loc[2]})")

print("\n--- Duplicated Classes ---")
for h, locations in classes.items():
    if len(locations) > 1:
        print(f"Duplicate class structure found ({len(locations)} occurrences):")
        for loc in locations:
            print(f"  - {loc[0]} : {loc[1]} (Line {loc[2]})")
