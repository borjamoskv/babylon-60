import os
import yaml
import time
import logging
import hashlib
from typing import Any

from uess_cortex_runtime import UESSCortexRuntime
from uess_sentinel_daemon import UESSSentinelDaemon

logger = logging.getLogger("cortex.ouroboros")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class UESSOuroborosEngine:
    """
    C5-REAL Ouroboros Engine.
    Self-rewriting SPEC loop.
    Reads DVF collapse signals from Sentinel DAEMON.
    Mutates the System SPEC and injects AST events into CORTEX Runtime
    to align execution with the new SPEC.
    """
    def __init__(self, spec_path: str, runtime: UESSCortexRuntime, daemon: UESSSentinelDaemon):
        self.spec_path = spec_path
        self.runtime = runtime
        self.daemon = daemon
        self.generation = 0
        
        if not os.path.exists(self.spec_path):
            self._write_default_spec()

    def _write_default_spec(self):
        default_spec = {
            "mode": "SELF_REWRITING",
            "termination": ["convergence", "entropy_limit", "operator_interrupt"],
            "swarm_parameters": {
                "max_entropy": 0.8,
                "error_tolerance": 0.5
            },
            "generation": 0
        }
        with open(self.spec_path, "w") as f:
            yaml.dump(default_spec, f)
        logger.info("Initialized default UESS Ouroboros SPEC.")

    def read_spec(self) -> dict[str, Any]:
        with open(self.spec_path, "r") as f:
            return yaml.safe_load(f)

    def write_spec(self, spec: dict[str, Any]):
        spec["generation"] = self.generation
        with open(self.spec_path, "w") as f:
            yaml.dump(spec, f)
        
        spec_hash = hashlib.sha256(yaml.dump(spec).encode()).hexdigest()
        logger.info(f"Ouroboros Rewrote SPEC. Gen: {self.generation} | Hash: {spec_hash[:16]}")
        
        # Emit rewrite event to global AOF
        self.runtime._emit_event("SPEC_REWRITE", 0, {"generation": self.generation, "hash": spec_hash})

    def measure_and_adapt(self) -> str:
        """
        1. Measure DVF state from Sentinel
        2. Adapt SPEC if DVF bounds are breached
        Returns status logic.
        """
        if self.daemon.dvf.identity_coherence < 0.5 or self.daemon.dvf.contradiction_index > 0.8:
            logger.warning("OUROBOROS TRIGGERED: DVF Bounds breached. Initiating Autopoiesis.")
            
            spec = self.read_spec()
            
            # Simple algorithmic self-correction (in a full LLM setup, this prompts the LLM)
            # We tighten swarm parameters to force convergence and drop entropy
            current_max_entropy = spec.get("swarm_parameters", {}).get("max_entropy", 0.8)
            spec["swarm_parameters"]["max_entropy"] = max(0.1, current_max_entropy * 0.8)
            spec["swarm_parameters"]["error_tolerance"] = max(0.1, spec["swarm_parameters"].get("error_tolerance", 0.5) * 0.8)
            
            self.generation += 1
            self.write_spec(spec)
            
            # Reset DAEMON bounds post-repair
            self.daemon.dvf.identity_coherence = 1.0
            self.daemon.dvf.contradiction_index = 0.0
            
            return "bifurcation_evolutiva"
            
        elif self.daemon.dvf.entropy_growth < 0.01 and self.daemon.dvf.identity_coherence > 0.95:
            return "convergence"
            
        return "stable"

    def run_ouroboros_loop(self, max_iterations: int = 10):
        logger.info("Starting OUROBOROS Engine Mode: SELF_REWRITING.")
        for i in range(max_iterations):
            logger.info(f"--- Ouroboros Epoch {i} ---")
            
            # 1. Execute Runtime Tick
            self.runtime.loop_cycle()
            
            # 2. Sentinel Observes Runtime AOF
            self.daemon.run_cycle()
            
            # 3. Ouroboros Measures DVF and Rewrites Spec
            state = self.measure_and_adapt()
            
            if state == "convergence":
                logger.info("OUROBOROS TERMINATION: Convergence Achieved.")
                break
                
            # Simulate external load to trigger DVF collapse
            if i == 2:
                self.daemon.dvf.identity_coherence = 0.2 # Force a breach
                
            time.sleep(0.5)

if __name__ == "__main__":
    # Integration Mock
    dummy_ast = "ouroboros_dummy_ast.py"
    with open(dummy_ast, "w") as f: f.write("def foo(): pass\n")
    
    runtime = UESSCortexRuntime(target_ast_file=dummy_ast)
    daemon = UESSSentinelDaemon(log_path=runtime.log_file)
    ouroboros = UESSOuroborosEngine(spec_path="cortex_spec.yaml", runtime=runtime, daemon=daemon)
    
    ouroboros.run_ouroboros_loop(max_iterations=5)
