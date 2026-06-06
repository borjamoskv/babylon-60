with open("cortex/engine/causal/advisory.py", encoding="utf-8") as f:
    content = f.read()

# Replace print(json.dumps(...)) with logger.info(...)
content = content.replace(
    'print(json.dumps(result, indent=2))',
    'logger.info("Advisory Result:\\n%s", json.dumps(result, indent=2))'
)

# Ensure logging is imported and logger is defined
if "import logging" not in content:
    content = "import logging\n" + content
if "logger = logging.getLogger(__name__)" not in content:
    content = content.replace("import logging\n", "import logging\nlogger = logging.getLogger(__name__)\n", 1)

with open("cortex/engine/causal/advisory.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Patched advisory.py")
