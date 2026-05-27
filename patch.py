import re
path = 'cortex/engine/swarm_10k.py'
with open(path, 'r') as f:
    code = f.read()
code = code.replace('logger.info("ANNIHILATE: Unlinked=%d, Closed=%d", unlinked_count, closed_count)', 'print(f"ANNIHILATE: Unlinked={unlinked_count}, Closed={closed_count}")')
with open(path, 'w') as f:
    f.write(code)
