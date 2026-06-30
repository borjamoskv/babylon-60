import subprocess
import re
import os

def run_mypy():
    print("Running mypy...")
    result = subprocess.run(["mypy", "cortex"], capture_output=True, text=True)
    return result.stdout + "\n" + result.stderr

def fix_unused_ignores():
    output = run_mypy()
    pattern = re.compile(r'^(?P<file>.+?):(?P<line>\d+): error: Unused "type: ignore" comment', re.MULTILINE)
    
    fixes_made = 0
    file_changes = {}

    for match in pattern.finditer(output):
        filepath = match.group("file")
        line_num = int(match.group("line")) - 1  # 0-indexed
        
        if filepath not in file_changes:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    file_changes[filepath] = f.readlines()
            except FileNotFoundError:
                continue
                
        lines = file_changes[filepath]
        if 0 <= line_num < len(lines):
            original = lines[line_num]
            # Strip the type: ignore
            lines[line_num] = re.sub(r'#\s*type:\s*ignore\s*(?:\[.*?\])?', '', original).rstrip() + '\n'
            # If it became an empty line and wasn't before, maybe we leave it, or strip trailing spaces
            if lines[line_num].strip() == "" and original.strip() != "":
                lines[line_num] = "\n"
            fixes_made += 1

    for filepath, lines in file_changes.items():
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)
            
    print(f"Macrophage Typing: Erradicados {fixes_made} 'type: ignore' inútiles.")

if __name__ == "__main__":
    fix_unused_ignores()
