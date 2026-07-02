import ast
import re


class CodeParser:
    def parse_python(self, code: str):
        result = {
            "classes": [],
            "functions": [],
            "imports": []
        }

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return result

        all_nodes = list(ast.walk(tree))
        result["classes"] = [n.name for n in all_nodes if isinstance(n, ast.ClassDef)]
        result["functions"] = [n.name for n in all_nodes if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        
        import_nodes = [n for n in all_nodes if isinstance(n, ast.Import)]
        import_from_nodes = [n for n in all_nodes if isinstance(n, ast.ImportFrom)]
        
        imports = [a.name for n in import_nodes for a in n.names]
        imports.extend(n.module or "" for n in import_from_nodes)
        
        result["imports"] = imports
        return result

    def parse_js(self, code: str):
        result = {
            "classes": [],
            "functions": [],
            "imports": []
        }

        # imports
        result["imports"] = re.findall(r'import\s+.*?from\s+[\'"](.+?)[\'"]', code)
        result["imports"] += re.findall(r'require\([\'"](.+?)[\'"]\)', code)

        # functions
        result["functions"] += re.findall(r'function\s+([A-Za-z0-9_]+)', code)
        result["functions"] += re.findall(r'const\s+([A-Za-z0-9_]+)\s*=\s*\(', code)

        # classes
        result["classes"] += re.findall(r'class\s+([A-Za-z0-9_]+)', code)

        return result
