import ast
import argparse
import sys
from pathlib import Path

class ASTProjector(ast.NodeTransformer):
    """
    Acts as the Maxwell's Demon for the Context Window.
    Prunes high-entropy (irrelevant) function bodies while keeping structural signatures intact.
    """
    def __init__(self, target_nodes):
        self.target_nodes = set(target_nodes)

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if node.name not in self.target_nodes:
            # Prune body but preserve docstring if present
            docstring = ast.get_docstring(node)
            if docstring:
                node.body = [ast.Expr(value=ast.Constant(value=docstring))]
            else:
                node.body = [ast.Pass()]
        return node

    def visit_AsyncFunctionDef(self, node):
        self.generic_visit(node)
        if node.name not in self.target_nodes:
            docstring = ast.get_docstring(node)
            if docstring:
                node.body = [ast.Expr(value=ast.Constant(value=docstring))]
            else:
                node.body = [ast.Pass()]
        return node

    def visit_ClassDef(self, node):
        self.generic_visit(node)
        # Class structure remains, only methods are pruned (handled above)
        return node

def project_ast(source_code, target_nodes):
    from cortex.engine.ast_validator import enforce_strict_types
    # [C5-REAL] Strict structural invariant validation before projection
    enforce_strict_types(source_code, filename="<ast_projector>")
    
    tree = ast.parse(source_code)
    projector = ASTProjector(target_nodes)
    projected_tree = projector.visit(tree)
    ast.fix_missing_locations(projected_tree)
    return ast.unparse(projected_tree)

def calculate_exergy_metrics(original_code, projected_code):
    # Approximation: 1 token ~ 4 chars
    orig_tokens = max(len(original_code) / 4, 1)
    proj_tokens = max(len(projected_code) / 4, 1)
    reduction = ((orig_tokens - proj_tokens) / orig_tokens) * 100
    
    # E_info(C) = V(C) / T(C). Assuming V(C) = 1 for a single verifiable unit of work.
    e_info_orig = 1 / orig_tokens
    e_info_proj = 1 / proj_tokens
    multiplier = e_info_proj / e_info_orig
    
    return orig_tokens, proj_tokens, reduction, multiplier

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="[C5-REAL] AST Projector - Context Exergy Maximizer")
    parser.add_argument("file", help="Source Python file")
    parser.add_argument("--targets", nargs="*", default=[], help="Target function/method names to preserve")
    args = parser.parse_args()

    filepath = Path(args.file)
    if not filepath.exists():
        print(f"Error: {filepath} not found.")
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()

    projected = project_ast(source, args.targets)
    orig_t, proj_t, red, mult = calculate_exergy_metrics(source, projected)

    print("=== [C5-REAL] AST PROJECTION (SZILARD ENGINE) ===")
    print(projected)
    print("\n=== THERMODYNAMIC METRICS: EXERGÍA INFORMACIONAL ===")
    print(f"Target Nodes Preserved: {args.targets if args.targets else 'None (Full Prune)'}")
    print(f"Original Tokens (approx): {orig_t:.0f}")
    print(f"Projected Tokens (approx): {proj_t:.0f}")
    print(f"Context Reduction (Entropy Purged): {red:.2f}%")
    print(f"E_info(C) Multiplier: {mult:.2f}x (Verifiable work per token)")
