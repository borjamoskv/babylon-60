import ast
import os
import sys
import logging
import time

# CORTEX Mirror Protocol v6.5 — The Epistemic Auditor
logging.basicConfig(level=logging.INFO, format="👁️ [MIRROR] %(message)s")


class MirrorAuditor:
    """Deterministic AST Auditor for CORTEX Source Code (Ω₂)."""

    def __init__(self, target_path: str):
        self.target_path = target_path
        self.findings = []
        self.exergy_score = 100.0

    def _calculate_complexity(self, tree):
        complexity = 1
        for node in ast.walk(tree):
            if isinstance(
                node,
                (
                    ast.If,
                    ast.While,
                    ast.For,
                    ast.ExceptHandler,
                    ast.IfExp,
                    ast.ListComp,
                    ast.DictComp,
                    ast.SetComp,
                    ast.GeneratorExp,
                ),
            ):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        return complexity

    def audit(self):
        """Performs structural analysis of the target file."""
        if not os.path.exists(self.target_path):
            return False

        try:
            with open(self.target_path) as f:
                tree = ast.parse(f.read())

            # 1. Hot Loop Analysis (Axiom Ω₆)
            for node in ast.walk(tree):
                if isinstance(node, ast.While) or isinstance(node, ast.For):
                    has_sleep = False
                    for subnode in ast.walk(node):
                        if (
                            isinstance(subnode, ast.Call)
                            and getattr(subnode.func, "id", "") == "sleep"
                        ):
                            has_sleep = True
                        if isinstance(subnode, ast.Attribute) and subnode.attr == "sleep":
                            has_sleep = True

                    if not has_sleep:
                        self.findings.append(
                            {
                                "type": "HOT_LOOP",
                                "severity": "CRITICAL",
                                "line": node.lineno,
                                "msg": "Loop detected without explicit throttle (Potential Exergy Leak)",
                            }
                        )
                        self.exergy_score -= 20.0

            # 2. Blockage Detection
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if getattr(node.func, "id", "") in ["print", "time.sleep"]:
                        self.findings.append(
                            {
                                "type": "SYNCHRONOUS_BLOCK",
                                "severity": "WARNING",
                                "line": node.lineno,
                                "msg": f"Synchronous {node.func.id} used in async context.",
                            }
                        )
                        self.exergy_score -= 5.0

            # 3. Structural Complexity
            complexity = self._calculate_complexity(tree)
            if complexity > 25:
                self.findings.append(
                    {
                        "type": "HIGH_COMPLEXITY",
                        "severity": "WARNING",
                        "line": 1,
                        "msg": f"High cyclomatic complexity detected ({complexity} > 25). Consider decomposing.",
                    }
                )
                self.exergy_score -= 10.0

            return True
        except Exception as e:
            logging.error("Mirror Audit Failure: %s", e)
            return False

    def report(self):
        """Generates a Sovereign remediation report."""
        report = {
            "timestamp": time.time(),
            "target": self.target_path,
            "exergy_score": max(0, self.exergy_score),
            "findings": self.findings,
            "status": "UNSTABLE" if self.exergy_score < 80 else "OPTIMAL",
        }
        return report


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python mirror_audit.py <target_file>")
        sys.exit(1)

    target = sys.argv[1]
    auditor = MirrorAuditor(target)
    if auditor.audit():
        import json

        print(json.dumps(auditor.report(), indent=2))
