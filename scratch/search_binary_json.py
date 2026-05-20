import re

binary_path = "/opt/homebrew/bin/jules"

with open(binary_path, "rb") as f:
    data = f.read()

# Search for common JSON keys or task field structures in the binary
keywords = [
    b"sourceContext",
    b"sourceId",
    b"environmentVariablesEnabled",
    b"agentConfig",
    b"taskOrigin",
]
for kw in keywords:
    print(f"Keyword: {kw.decode('ascii')}")
    # Let's find occurrences and extract nearby bytes
    idx = 0
    while True:
        idx = data.find(kw, idx)
        if idx == -1:
            break
        start = max(0, idx - 100)
        end = min(len(data), idx + 200)
        chunk = data[start:end]
        # Clean up binary for printing
        clean_chunk = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
        print(f"  Position {idx}: {clean_chunk}")
        idx += len(kw)
