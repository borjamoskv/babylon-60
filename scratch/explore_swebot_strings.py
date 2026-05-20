import re

binary_path = "/opt/homebrew/bin/jules"

with open(binary_path, "rb") as f:
    data = f.read()

# Extract all ASCII-like byte sequences
pattern = re.compile(b"[a-zA-Z0-9_/.:\\-]{4,}")

matches = []
for m in pattern.finditer(data):
    s = m.group(0).decode("ascii", errors="ignore")
    if "swebot" in s.lower() or "jules" in s.lower():
        # Get surrounding strings (up to 5 before and after)
        start_idx = max(0, data.rfind(b"\x00", 0, m.start()) + 1)
        end_idx = data.find(b"\x00", m.end())
        if end_idx == -1:
            end_idx = m.end()
        raw_str = data[start_idx:end_idx].decode("utf-8", errors="ignore")
        matches.append((m.start(), s, raw_str))

# Sort by position in binary
matches.sort()
print(f"Found {len(matches)} matches:")
for pos, s, raw in matches[:150]:
    print(f"[{pos}]: {s!r} | full: {raw!r}")
