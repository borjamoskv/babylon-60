import re

binary_path = "/opt/homebrew/bin/jules"

with open(binary_path, "rb") as f:
    data = f.read()

pattern = re.compile(b"https?://[a-zA-Z0-9_/.:\\-%?&=]+")

matches = []
for m in pattern.finditer(data):
    try:
        s = m.group(0).decode("ascii")
        matches.append(s)
    except:
        pass

unique_matches = sorted(list(set(matches)))
print(f"Found {len(unique_matches)} HTTP/HTTPS URLs:")
for m in unique_matches:
    print(m)
