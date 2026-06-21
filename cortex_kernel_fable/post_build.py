import os
import re
import subprocess
import sys


def post_build():
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../cortex/engine/fable_out"))
    print(f"Running post-build cleanups on: {out_dir}")
    
    if not os.path.exists(out_dir):
        print(f"Error: Output directory {out_dir} does not exist.")
        sys.exit(1)
        
    # Process all Python files in the output directory recursively
    for root, _, files in os.walk(out_dir):
        for file in files:
            if not file.endswith(".py"):
                continue
                
            filepath = os.path.join(root, file)
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
                
            # 1. Replace relative/absolute module imports from Fable's 'src' directory
            rel_dir = os.path.relpath(root, out_dir)
            if rel_dir == ".":
                new_content = re.sub(r"from src\.", "from .src.", content)
            else:
                new_content = re.sub(r"from src\.", "from .", content)
            
            # 2. Replace Python 3.12 type alias statements 'type X = Y' with Python 3.10 compatible 'X = Y'
            # Look for lines starting with 'type ' followed by an identifier and ' = '
            new_content = re.sub(r"^type\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=", r"\1 =", new_content, flags=re.MULTILINE)
            
            # 3. Fix B023 late binding of loop variables in closures (e.g. maxwell_demon.py)
            new_content = re.sub(
                r"def predicate\(tupled_arg:\s*tuple\[uint32,\s*str\],\s*this:\s*Any\s*=\s*this\)\s*->\s*bool:",
                "def predicate(tupled_arg: tuple[uint32, str], this: Any = this, h: uint32 = h) -> bool:",
                new_content
            )
            
            # Save if changed
            if new_content != content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Processed: {os.path.relpath(filepath, out_dir)}")
                
    # Run ruff to format and fix auto-fixable errors (like unused imports, sorting)
    print("Running ruff format and lint auto-fixes...")
    try:
        # Run ruff check with --fix
        subprocess.run(
            ["ruff", "check", "--fix", out_dir],
            check=False,
            capture_output=True
        )
        # Run ruff format
        subprocess.run(
            ["ruff", "format", out_dir],
            check=False,
            capture_output=True
        )
        print("Ruff cleanup complete.")
    except Exception as e:
        print(f"Warning: Could not run ruff: {e}")

if __name__ == "__main__":
    post_build()
