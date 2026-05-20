import re

binary_path = "/opt/homebrew/bin/jules"

with open(binary_path, "rb") as f:
    data = f.read()

# Let's search for "AgentConfig" in the binary and print Go struct info or strings around it
# Go binaries have runtime type info which includes field names of structs.
# Let's search for "AgentConfig" string (case sensitive) and print ASCII sequences around it.
keyword = b"AgentConfig"
idx = 0
while True:
    idx = data.find(keyword, idx)
    if idx == -1:
        break
    start = max(0, idx - 200)
    end = min(len(data), idx + 200)
    chunk = data[start:end]
    clean_chunk = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
    print(f"Position {idx}: {clean_chunk}")
    idx += len(keyword)
