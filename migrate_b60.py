import os
import re

TARGET_DIR = "babylon60/engine/"

def migrate_file(filepath: str):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Skip if no float
    if 'float' not in content:
        return

    lines = content.split('\n')
    new_lines = []
    imported = False
    modified = False

    for line in lines:
        if not imported and 'from dataclasses' in line or 'import' in line:
            # We will inject the import right after future annotations if we find it, or at the first import
            pass
            
        # Match: var_name: float = 5.0
        match_assignment = re.match(r'^(\s*)(\w+):\s*float\s*=\s*([0-9.]+)\s*(.*)$', line)
        if match_assignment:
            indent, var, val, rest = match_assignment.groups()
            new_lines.append(f"{indent}{var}: Babylon60 = Babylon60.from_float({val}) {rest}".rstrip())
            modified = True
            continue
            
        # Match type hints without assignment: var_name: float
        match_hint = re.match(r'^(\s*)(\w+):\s*float\s*(.*)$', line)
        if match_hint and not 'def ' in line and not 'return ' in line:
            indent, var, rest = match_hint.groups()
            new_lines.append(f"{indent}{var}: Babylon60 {rest}".rstrip())
            modified = True
            continue

        # Try to catch function returns: -> float:
        if '-> float:' in line:
            line = line.replace('-> float:', '-> Babylon60:')
            modified = True
            
        # Try to catch list[float] or dict[str, float]
        if 'float]' in line or 'float,' in line:
            line = re.sub(r'\bfloat\b', 'Babylon60', line)
            modified = True
            
        new_lines.append(line)

    if modified:
        # Inject import
        for i, line in enumerate(new_lines):
            if 'from __future__ import annotations' in line:
                new_lines.insert(i + 1, "from babylon60.math.babylon import Babylon60")
                break
        else:
            new_lines.insert(0, "from babylon60.math.babylon import Babylon60")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        print(f"Migrated {filepath}")

def main():
    for root, _, files in os.walk(TARGET_DIR):
        for file in files:
            if file.endswith('.py') and not file.startswith('test_'):
                migrate_file(os.path.join(root, file))

if __name__ == '__main__':
    main()
