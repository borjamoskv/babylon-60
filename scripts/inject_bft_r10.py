
import os
import sys
import glob



SQLITE_PATCH = """
"""

AIOSQLITE_PATCH = """
"""

def patch_file(filepath):
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except Exception as e:
        return False
        
    if "# --- C5-REAL BFT PATCH (R10) ---" in content or "# --- C5-REAL BFT PATCH AIOSQLITE (R10) ---" in content:
        return False # Already patched
    patched = False
    if "import sqlite3" in content or "from sqlite3" in content:
        content = content.replace("import sqlite3\n", "import sqlite3\n" + SQLITE_PATCH)
        patched = True
    if "import aiosqlite" in content:
        content = content.replace("import aiosqlite\n", "import aiosqlite\n" + AIOSQLITE_PATCH)
        patched = True
    if patched:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"[+] Patched BFT R10 in: {filepath}")
        return True
    return False
def scan_and_patch(directory):
    count = 0
    for root, _, files in os.walk(directory):
        if '.venv' in root or '.git' in root or 'node_modules' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                if patch_file(path):
                    count += 1
    print(f"[*] Total files patched in {directory}: {count}")
if __name__ == "__main__":
    targets = [
        "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist",
        "/Users/borjafernandezangulo/10_PROJECTS/cortex-meta",
        "/Users/borjafernandezangulo/10_PROJECTS/cortex-head"
    ]
    for target in targets:
        if os.path.exists(target):
            scan_and_patch(target)
