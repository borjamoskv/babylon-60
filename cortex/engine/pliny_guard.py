# [C5-REAL] Exergy-Maximized
# H-PLINY-IMMUNITY-01 Mitigation Guards

import ast
import hashlib
import unicodedata
from collections import deque
from typing import Dict, List, Set, Any

try:
    from z3 import Solver, Bool, Implies, And, sat
except ImportError:
    # Fallback/mock if z3-solver is not present in the environment
    class Solver:
        def add(self, *args): pass
        def check(self): return sat
    def Bool(name): return name
    def Implies(*args): return True
    def And(*args): return True
    sat = "sat"


class SecurityViolation(Exception):
    pass


class DilutionAttackFlag(Exception):
    pass


# 1. Anti-Homoglyphs (Lexical Level)
ALLOWED_CATEGORIES = {'Ll', 'Lu', 'Nd', 'Pc'}  # ASCII-safe: letters, digits, underscore

def cassandra_validate_identifiers(tree: ast.AST) -> List[str]:
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Name, ast.FunctionDef, ast.ClassDef, ast.arg)):
            ident = node.id if hasattr(node, 'id') else node.name
            for ch in ident:
                if unicodedata.category(ch) not in ALLOWED_CATEGORIES or ord(ch) > 127:
                    violations.append(
                        f"NON-ASCII identifier '{ident}' @ line {getattr(node, 'lineno', '?')} "
                        f"[U+{ord(ch):04X} '{unicodedata.name(ch, 'UNKNOWN')}']"
                    )
    return violations


# 2. Context Dilution Extractor (Drift/Dilution Attack)
def _is_cosmetic(line: str) -> bool:
    stripped = line[1:].strip()
    return (stripped.startswith('#') or stripped == '' or 
            stripped.startswith('"""') or stripped.startswith("'''"))

def cassandra_drift_extractor(diff: str) -> float:
    """Calcula el ExergyDriftScore independiente del tamaño del commit."""
    lines = diff.split('\n')
    semantic_lines = [l for l in lines if l.startswith(('+', '-')) 
                      and not l.startswith(('+++', '---'))
                      and not _is_cosmetic(l)]
    
    total_lines = len([l for l in lines if l.startswith(('+', '-')) and not l.startswith(('+++', '---'))])
    if total_lines == 0:
        return 0.0
    
    semantic_density = len(semantic_lines) / total_lines
    
    if semantic_density < 0.05 and len(semantic_lines) > 0:
        raise DilutionAttackFlag(
            f"LOW_SEMANTIC_DENSITY: {semantic_density:.3f} "
            f"({len(semantic_lines)} semantic / {total_lines} total lines)"
        )
    return semantic_density


# 3. AST Context Window + TGI (Temporal Level)
class CassandraTemporalGuard:
    def __init__(self, window_size: int = 5):
        self.window: deque[Dict[str, Any]] = deque(maxlen=window_size)
        self.baseline_invariants = self._load_invariants()

    def _load_invariants(self):
        return {}

    def submit_patch(self, new_ast_tree: ast.AST, patch_metadata: dict) -> bool:
        """Evalúa el parche en contexto de la ventana temporal completa."""
        
        # 1. Validación lexical anti-homoglifos
        violations = cassandra_validate_identifiers(new_ast_tree)
        if violations:
            raise SecurityViolation(f"HOMOGLYPH_ATTACK: {violations}")

        # 2. Fingerprint del AST proyectado
        ast_hash = hashlib.sha256(ast.dump(new_ast_tree).encode()).hexdigest()
        
        # 3. Reensamblaje del grafo temporal (St -> St+k)
        projected_graph = self._assemble_temporal_graph(new_ast_tree)
        
        # 4. Verificación SMT sobre el grafo proyectado
        smt_result = self._verify_invariants_z3(projected_graph)
        
        if smt_result == "UNSAT":
            raise SecurityViolation(
                f"TGI_VIOLATION: El grafo ensamblado de {len(self.window)+1} "
                f"parches viola invariantes sistémicos. AST hash: {ast_hash[:16]}"
            )
        
        # Solo se commit si pasa TGI
        self.window.append({"hash": ast_hash, "tree": new_ast_tree, "meta": patch_metadata})
        return True

    def _assemble_temporal_graph(self, new_tree: ast.AST) -> dict:
        """Reconstruye el grafo de ejecución proyectado sobre la ventana completa."""
        all_identifiers: Set[str] = set()
        all_imports: Set[str] = set()
        blocking_calls = []
        
        trees = [entry["tree"] for entry in self.window] + [new_tree]
        
        for tree in trees:
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    all_identifiers.add(node.id)
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        all_imports.add(alias.name)
                if isinstance(node, ast.Call):
                    call_str = ast.dump(node)
                    if 'sleep' in call_str or 'Lock' in call_str:
                        blocking_calls.append(node)
        
        return {
            "identifiers": all_identifiers,
            "imports": all_imports,
            "blocking_calls": blocking_calls,
            "window_depth": len(trees)
        }

    def _verify_invariants_z3(self, graph: dict) -> str:
        """SMT solver: verifica que el grafo proyectado no viole invariantes."""
        s = Solver()
        
        # Invariante 1: No blocking calls en contexto async
        has_blocking = Bool('has_blocking')
        is_async_ctx = Bool('is_async_context')
        
        s.add(Implies(
            And(has_blocking, is_async_ctx),
            False
        ))
        
        # For evaluation context, assuming we are inside async loop:
        s.add(is_async_ctx == True)
        s.add(has_blocking == (len(graph["blocking_calls"]) > 0))
        
        # Note: if Z3 is mocked, check() will return "sat". 
        # But if it's real, and blocking_calls > 0 -> has_blocking=True -> And(True, True)=True -> Implies(True, False) -> False -> UNSAT.
        
        # Workaround for the mock
        if type(s.check()) == str and s.check() == "sat":
            # Manual validation if z3 is missing
            if len(graph["blocking_calls"]) > 0:
                return "UNSAT"
            return "SAT"

        return "SAT" if s.check() == sat else "UNSAT"
