import re

binary_path = "/opt/homebrew/bin/jules"

with open(binary_path, "rb") as f:
    data = f.read()

# Let's find all json tags of struct fields: json:"..."
matches = re.findall(b'json:"([^"]+)"', data)
unique_tags = sorted(list(set(m.decode("utf-8", errors="ignore") for m in matches)))
print(f"Total unique json tags: {len(unique_tags)}")
for tag in unique_tags:
    if any(kwd in tag.lower() for kwd in ["model", "agent", "config", "image", "search"]):
        print(f"  Tag: {tag}")
