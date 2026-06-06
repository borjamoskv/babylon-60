import re

with open("cortex/engine/runtime_kernel.py", encoding="utf-8") as f:
    content = f.read()

# 1. fix json.dump
content = content.replace(
    'json.dump(asdict(state), f)',
    'json.dump(asdict(state), f, default=str)'
)

# 2. fix json.load and instantiation
# where we do:
# data = json.load(f)
# return CortexState(**data)
# We need to cast back to Decimal.
post_init_code = """
    def __post_init__(self):
        self.exergy = Decimal(str(self.exergy))
        self.entropy = Decimal(str(self.entropy))
        self.drift = Decimal(str(self.drift))
        self.cost = Decimal(str(self.cost))
"""
# insert __post_init__ into CortexState
content = re.sub(
    r"(class CortexState:.*?tick_count: int = 0)",
    r"\1\n" + post_init_code,
    content,
    flags=re.DOTALL
)

with open("cortex/engine/runtime_kernel.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Patched runtime_kernel.py")
