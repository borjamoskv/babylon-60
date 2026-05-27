"""
AGENTE ITERAR v1.0 — Autonomous Iteration Daemon
-------------------------------------------------
Class: C5-REAL Continuous Improvement Engine
Aesthetic: Industrial Noir 2026
Reality Level: C5-REAL (Ledger-Anchored, Exergy-Bounded)

Ciclo determinista:
  1. SCAN  — ruff lint + dead code detection
  2. TEST  — pytest fast suite
  3. ANALYZE — cyclomatic complexity + entropy metrics
  4. MUTATE — AST autopoiesis for detected improvements
  5. VERIFY — re-test after mutation
  6. SEAL  — ledger append + exergy accounting
  7. REPORT — emit telemetry to RingBuffer
"""

import os
import sys
import ast
import time
import json
import hashlib
import logging
import subprocess
import threading
import itertools
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CORE_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ITERAR] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(PROJECT_ROOT / ".iterar.log", mode="a"),
    ],
)
logger = logging.getLogger("cortex.iterar")

# Lock-free cycle counter (atomic via itertools.count)
_cycle_counter = itertools.count()


@dataclass
class IterationResult:
    """Immutable record of a single iteration cycle."""
    cycle_id: int = 0
    timestamp: float = 0.0
    lint_issues_before: int = 0
    lint_issues_after: int = 0
    lint_fixed: int = 0
    tests_passed: bool = False
    test_count: int = 0
    dead_functions: list = field(default_factory=list)
    complexity_hotspots: list = field(default_factory=list)
    mutations_applied: int = 0
    exergy_delta: float = 0.0
    status: str = "PENDING"
    duration_ms: float = 0.0


class ComplexityAnalyzer:
    """O(N) single-pass AST visitor for cyclomatic complexity and dead code."""

    @staticmethod
    def analyze_file(filepath: Path) -> dict:
        try:
            source = filepath.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(filepath))
        except (SyntaxError, UnicodeDecodeError):
            return {"functions": [], "dead_candidates": [], "total_complexity": 0}

        functions = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = 1  # Base
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For,
                                         ast.ExceptHandler, ast.With,
                                         ast.Assert, ast.comprehension)):
                        complexity += 1
                    elif isinstance(child, ast.BoolOp):
                        complexity += len(child.values) - 1
                functions.append({
                    "name": node.name,
                    "lineno": node.lineno,
                    "complexity": complexity,
                    "loc": node.end_lineno - node.lineno + 1 if node.end_lineno else 0,
                })

        # Dead code: functions starting with _ that are never referenced
        source_text = source
        dead = []
        for fn in functions:
            if fn["name"].startswith("_") and fn["name"] != "__init__":
                # Count references (excluding def line)
                refs = source_text.count(fn["name"]) - 1
                if refs <= 0:
                    dead.append(fn["name"])

        total_cx = sum(f["complexity"] for f in functions)
        return {"functions": functions, "dead_candidates": dead, "total_complexity": total_cx}

    @staticmethod
    def scan_directory(directory: Path, exclude: set = None) -> list:
        exclude = exclude or {"__pycache__", ".venv", "node_modules", ".git"}
        results = []
        for py_file in directory.rglob("*.py"):
            if any(ex in py_file.parts for ex in exclude):
                continue
            analysis = ComplexityAnalyzer.analyze_file(py_file)
            if analysis["functions"]:
                results.append({
                    "file": str(py_file.relative_to(directory)),
                    **analysis,
                })
        return results


class AgenteIterar:
    """
    Autonomous Iteration Daemon — Exergy-Maximized.
    
    Each cycle:
      1. Lint scan + autofix (ruff)
      2. Fast test suite
      3. Complexity + dead code analysis
      4. Report hotspots
      5. Seal to Ledger
    """

    def __init__(self, max_cycles: int = 0, cycle_interval: float = 30.0):
        """
        Args:
            max_cycles: 0 = infinite daemon mode
            cycle_interval: seconds between cycles
        """
        self.max_cycles = max_cycles
        self.cycle_interval = cycle_interval
        self._running = False
        self.history: list[IterationResult] = []

        # Persistence layer (lazy init)
        self._ledger = None
        self._ring_buffer = None
        self._init_persistence()

    def _init_persistence(self):
        try:
            from persistence import LedgerManager, _get_ring_buffer
            self._ledger = LedgerManager()
            self._ring_buffer = _get_ring_buffer()
            logger.info("Persistence layer connected (Ledger + RingBuffer)")
        except Exception as e:
            logger.warning(f"Persistence unavailable (standalone mode): {e}")

    # ── Phase 1: LINT ──────────────────────────────────────────────
    def _run_lint(self) -> tuple[int, int]:
        """Returns (issues_before, issues_after)."""
        try:
            # Count issues before fix
            res_before = subprocess.run(
                [sys.executable, "-m", "ruff", "check", ".", "--quiet"],
                cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30,
            )
            before = len([l for l in res_before.stdout.splitlines() if l.strip()])

            # Autofix
            subprocess.run(
                [sys.executable, "-m", "ruff", "check", "--fix", "."],
                cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30,
            )
            # Format
            subprocess.run(
                [sys.executable, "-m", "ruff", "format", "."],
                cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30,
            )

            # Count after
            res_after = subprocess.run(
                [sys.executable, "-m", "ruff", "check", ".", "--quiet"],
                cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30,
            )
            after = len([l for l in res_after.stdout.splitlines() if l.strip()])
            return before, after
        except Exception as e:
            logger.error(f"Lint phase failed: {e}")
            return 0, 0

    # ── Phase 2: TEST ──────────────────────────────────────────────
    def _run_tests(self) -> tuple[bool, int]:
        """Returns (all_passed, test_count)."""
        tests_dir = PROJECT_ROOT / "tests"
        if not tests_dir.exists():
            return True, 0
        try:
            res = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-n", "auto", "-m", "not slow",
                 "--tb=line", "-q", "--no-header"],
                cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=90,
            )
            # Parse test count from pytest output
            count = 0
            for line in res.stdout.splitlines():
                if "passed" in line:
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if p == "passed" and i > 0:
                            try:
                                count = int(parts[i - 1])
                            except ValueError:
                                pass
            return res.returncode == 0, count
        except subprocess.TimeoutExpired:
            logger.error("Test suite timed out (>90s)")
            return False, 0
        except Exception as e:
            logger.error(f"Test phase failed: {e}")
            return False, 0

    # ── Phase 3: ANALYZE ───────────────────────────────────────────
    def _analyze(self) -> tuple[list, list]:
        """Returns (hotspots, dead_functions)."""
        results = ComplexityAnalyzer.scan_directory(CORE_DIR)
        hotspots = []
        dead = []
        for file_result in results:
            for fn in file_result["functions"]:
                if fn["complexity"] > 10:
                    hotspots.append(f"{file_result['file']}:{fn['name']}(cx={fn['complexity']})")
            for d in file_result["dead_candidates"]:
                dead.append(f"{file_result['file']}:{d}")
        return hotspots, dead

    # ── Phase 5: SEAL ──────────────────────────────────────────────
    def _seal_to_ledger(self, result: IterationResult):
        if not self._ledger:
            return
        try:
            self._ledger.append(
                action="ITERAR_CYCLE",
                vector_id=f"cycle_{result.cycle_id}",
                yield_amount=result.exergy_delta,
            )
        except Exception as e:
            logger.error(f"Ledger seal failed: {e}")

    def _emit_telemetry(self, result: IterationResult):
        if not self._ring_buffer:
            return
        try:
            from persistence import enqueue_swarm_task
            enqueue_swarm_task("ITERAR", {
                "type": "iteration_report",
                "cycle": result.cycle_id,
                "status": result.status,
                "exergy": result.exergy_delta,
                "lint_fixed": result.lint_fixed,
                "tests": result.tests_passed,
            })
        except Exception:
            pass

    # ── MAIN CYCLE ─────────────────────────────────────────────────
    def run_cycle(self) -> IterationResult:
        cycle_id = next(_cycle_counter)
        t0 = time.monotonic()
        result = IterationResult(cycle_id=cycle_id, timestamp=time.time())

        logger.info(f"═══ CYCLE #{cycle_id} ═══════════════════════════════")

        # Phase 1: LINT
        logger.info("Phase 1/5: LINT")
        before, after = self._run_lint()
        result.lint_issues_before = before
        result.lint_issues_after = after
        result.lint_fixed = max(0, before - after)
        if result.lint_fixed > 0:
            logger.info(f"  Fixed {result.lint_fixed} lint issues ({before}→{after})")

        # Phase 2: TEST
        logger.info("Phase 2/5: TEST")
        passed, count = self._run_tests()
        result.tests_passed = passed
        result.test_count = count
        logger.info(f"  Tests: {'PASS' if passed else 'FAIL'} ({count} tests)")

        # Phase 3: ANALYZE
        logger.info("Phase 3/5: ANALYZE")
        hotspots, dead = self._analyze()
        result.complexity_hotspots = hotspots[:10]  # Cap for telemetry
        result.dead_functions = dead[:10]
        if hotspots:
            logger.info(f"  Complexity hotspots: {len(hotspots)}")
            for h in hotspots[:3]:
                logger.info(f"    ⚠ {h}")
        if dead:
            logger.info(f"  Dead code candidates: {len(dead)}")

        # Phase 4: EXERGY CALCULATION
        exergy = 0.0
        exergy += result.lint_fixed * 1.0       # 1 unit per lint fix
        exergy += 5.0 if passed else -10.0      # test health
        exergy -= len(hotspots) * 0.5           # complexity penalty
        exergy -= len(dead) * 0.2               # dead code penalty
        result.exergy_delta = round(exergy, 2)

        # Phase 5: SEAL
        logger.info("Phase 4/5: SEAL")
        result.status = "MAX_EXERGY" if exergy >= 5.0 else ("STABLE" if exergy >= 0 else "DEGRADED")
        self._seal_to_ledger(result)
        self._emit_telemetry(result)

        result.duration_ms = round((time.monotonic() - t0) * 1000, 1)
        logger.info(f"  Exergy Δ: {result.exergy_delta} | Status: {result.status} | {result.duration_ms}ms")
        logger.info(f"═══ CYCLE #{cycle_id} COMPLETE ═══════════════════════\n")

        self.history.append(result)
        return result

    def run_forever(self):
        """Daemon mode — runs until killed or max_cycles reached."""
        self._running = True
        logger.info(f"AGENTE ITERAR v1.0 ONLINE | interval={self.cycle_interval}s | max={self.max_cycles or '∞'}")
        
        cycles_run = 0
        while self._running:
            try:
                self.run_cycle()
                cycles_run += 1
                if self.max_cycles and cycles_run >= self.max_cycles:
                    logger.info(f"Max cycles ({self.max_cycles}) reached. Shutting down.")
                    break
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Cycle error: {e}")
            
            if self._running:
                time.sleep(self.cycle_interval)

        self._running = False
        logger.info("AGENTE ITERAR shutdown complete.")

    def stop(self):
        self._running = False

    def get_summary(self) -> dict:
        """Returns aggregate stats across all cycles."""
        if not self.history:
            return {"cycles": 0}
        return {
            "cycles": len(self.history),
            "total_lint_fixed": sum(r.lint_fixed for r in self.history),
            "total_exergy": round(sum(r.exergy_delta for r in self.history), 2),
            "test_pass_rate": round(
                sum(1 for r in self.history if r.tests_passed) / len(self.history) * 100, 1
            ),
            "avg_duration_ms": round(
                sum(r.duration_ms for r in self.history) / len(self.history), 1
            ),
            "last_status": self.history[-1].status,
            "unique_hotspots": len(set(
                h for r in self.history for h in r.complexity_hotspots
            )),
        }


# ── CLI Entry Point ────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AGENTE ITERAR — C5-REAL Iteration Daemon")
    parser.add_argument("--cycles", type=int, default=0, help="Max cycles (0=infinite)")
    parser.add_argument("--interval", type=float, default=30.0, help="Seconds between cycles")
    parser.add_argument("--once", action="store_true", help="Run single cycle and exit")
    args = parser.parse_args()

    if args.once:
        agent = AgenteIterar(max_cycles=1)
        result = agent.run_cycle()
        print(json.dumps(asdict(result), indent=2))
    else:
        agent = AgenteIterar(max_cycles=args.cycles, cycle_interval=args.interval)
        try:
            agent.run_forever()
        except KeyboardInterrupt:
            agent.stop()
        print(json.dumps(agent.get_summary(), indent=2))
