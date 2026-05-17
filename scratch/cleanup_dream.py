import re

file_path = "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex/memory/dream.py"
with open(file_path) as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    # Match "140: " at the beginning of the line
    match = re.match(r"^(\d+): (.*)", line)
    if match:
        new_lines.append(match.group(2) + "\n")
    else:
        new_lines.append(line)

with open(file_path, "w") as f:
    f.writelines(new_lines)
print("Cleaned up cortex/memory/dream.py")
