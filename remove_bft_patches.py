import os
import re


def strip_bft_patches(filepath):
    with open(filepath) as f:
        content = f.read()

    # Find the patch (both aiosqlite and sqlite3 variants)
    pattern = re.compile(r'(# --- C5-REAL BFT PATCH.*?\n# -+\n)', re.DOTALL)
    patches = pattern.findall(content)
    if not patches:
        return False
    new_content = content
    for patch in patches:
        new_content = new_content.replace(patch, '')
    # Clean up double blank lines that might be left at the top
    new_content = re.sub(r'^\n\n+', '\n', new_content)
    new_content = new_content.lstrip('\n')
    # Restore the __future__ spacing if needed
    if new_content.startswith('from __future__') and '\n\n' not in new_content[:100]:
        new_content = new_content.replace('\nimport', '\n\nimport', 1)
    with open(filepath, 'w') as f:
        f.write(new_content)
    return True
changed_files = []
for root, dirs, files in os.walk('/Users/borjafernandezangulo/10_PROJECTS/cortex-persist'):
    if '.venv' in root or '.git' in root or 'legacy_research' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            if strip_bft_patches(filepath):
                changed_files.append(filepath)
print(f"Removed BFT patches from {len(changed_files)} files.")
