import re

binary_path = "/opt/homebrew/bin/jules"

with open(binary_path, "rb") as f:
    data = f.read()

pattern = re.compile(b"[a-zA-Z0-9_/.:%{} -]{4,}")

matches = []
for m in pattern.finditer(data):
    s = m.group(0).decode("ascii", errors="ignore")
    if "project" in s.lower() or "location" in s.lower() or "source" in s.lower():
        matches.append(s)

unique_matches = sorted(list(set(matches)))
print(f"Found {len(unique_matches)} matches:")
for m in unique_matches[:150]:
    print(m)
