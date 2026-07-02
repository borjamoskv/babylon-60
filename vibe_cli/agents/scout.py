from pathlib import Path


class ScoutAgent:
    def run(self, state):
        root = Path(state.root_path)
        suffixes = {".py", ".js", ".ts", ".tsx", ".md", ".json", ".yaml", ".yml"}

        state.files = [
            str(path) for path in root.rglob("*")
            if path.is_file() and path.suffix in suffixes
        ]

        state.stack = {
            "python": any(f.endswith(".py") for f in state.files),
            "node": any("package.json" in f for f in state.files),
            "react": any(f.endswith(".tsx") for f in state.files),
            "fastapi": False,
            "django": False,
            "express": False,
            "nextjs": False,
            "markdown_docs": any(f.endswith(".md") for f in state.files)
        }

        self._detect_frameworks(state.files, state.stack)
        return state

    def _detect_frameworks(self, files: list[str], stack: dict[str, bool]):
        for f in files:
            if f.endswith(".py"):
                self._check_python_file(f, stack)
            elif f.endswith(".json") and "package.json" in f:
                self._check_json_file(f, stack)

    def _check_python_file(self, file_path: str, stack: dict[str, bool]):
        try:
            content = Path(file_path).read_text(errors="ignore")[:2000]
            if "from fastapi" in content or "import fastapi" in content:
                stack["fastapi"] = True
            if "from django" in content or "import django" in content:
                stack["django"] = True
        except Exception:
            pass

    def _check_json_file(self, file_path: str, stack: dict[str, bool]):
        try:
            content = Path(file_path).read_text(errors="ignore")
            if "next" in content:
                stack["nextjs"] = True
            if "express" in content:
                stack["express"] = True
        except Exception:
            pass

