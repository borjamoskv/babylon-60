import re

binary_path = "/opt/homebrew/bin/jules"

with open(binary_path, "rb") as f:
    data = f.read()

# Extract ASCII strings of length >= 4
strings = re.findall(b"[a-zA-Z0-9_/.: -]{4,}", data)

# Search for patterns containing sweBot, swebot, or typical api endpoints
matches = []
for s in strings:
    try:
        s_str = s.decode("ascii")
        if any(
            x in s_str.lower()
            for x in ["swebot", "swe_bot", "jules", "source", "session", "activities"]
        ):
            matches.append(s_str)
    except Exception:
        pass

# Print unique matches
unique_matches = sorted(list(set(matches)))
print(f"Total matches found: {len(unique_matches)}")
for m in unique_matches[:100]:
    print(m)
