import os
import re

def strip_bft_patches(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Match `# --- C5-REAL BFT PATCH` optionally indented, followed by non-greedy anything,
    # followed by `# -----` optionally indented.
    # The `.*?` will span multiple lines because of re.DOTALL.
    # To prevent runaway deletions, we ensure the matched length doesn't exceed 2000 characters.
    pattern = re.compile(r'([ \t]*# --- C5-REAL BFT PATCH.*?# -{10,}[ \t]*\n)', re.DOTALL)
    patches = pattern.findall(content)
    if not patches:
        return False
    new_content = content
    modified = False
    for patch in patches:
        if len(patch) < 1500: # A valid BFT patch block is around 400-800 characters
            new_content = new_content.replace(patch, '')
            modified = True
        else:
            print(f"Skipping dangerously large match in {filepath} ({len(patch)} chars)")
    if modified:
        with open(filepath, 'w') as f:
            f.write(new_content)
        return True
    return False
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
