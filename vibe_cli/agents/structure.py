from pathlib import Path

from core.parser import CodeParser


class StructureAgent:
    def __init__(self):
        self.parser = CodeParser()

    def run(self, state):
        state.code_structure = {}
        for file in state.files:
            self._process_file(file, state.code_structure)
        return state

    def _process_file(self, file_path: str, code_structure: dict):
        try:
            content = Path(file_path).read_text(errors="ignore")
            if file_path.endswith(".py"):
                code_structure[file_path] = self.parser.parse_python(content)
            elif file_path.endswith((".js", ".ts", ".tsx", ".jsx")):
                code_structure[file_path] = self.parser.parse_js(content)
        except Exception:
            pass

