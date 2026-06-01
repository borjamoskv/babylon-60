import ast
import hashlib
import time
import logging
from typing import Dict, Any, List
from autopoiesis_ast import ASTAutopoiesisEngine
from uess_swarm_scheduler import UESSSwarmScheduler, AgentRole

logger = logging.getLogger("cortex.uess_ast_mutation")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class UESSAstMutationEngine:
    """
    C5-REAL AST Mutation Engine.
    Subscribes to UESS `AstMutate` events and applies semantic graph transformations.
    Integrates directly with the UESS v2 Swarm Scheduler to enforce causal invariants.
    """
    def __init__(self, target_file: str, scheduler: UESSSwarmScheduler):
        self.target_file = target_file
        self.scheduler = scheduler
        self.autopoiesis = ASTAutopoiesisEngine(target_file)
        self.semantic_graph: Dict[str, Any] = {}
        self._build_semantic_graph()
        
    def _build_semantic_graph(self):
        """Compiles AST into a semantic dependency DAG."""
        for node in ast.walk(self.autopoiesis.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                deps = [n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)]
                self.semantic_graph[node.name] = {
                    "deps": list(set(deps)),
                    "complexity": len(list(ast.walk(node))),
                    "hash": hashlib.sha256(ast.unparse(node).encode()).hexdigest()
                }
        logger.info(f"Semantic Graph Built. {len(self.semantic_graph)} nodes indexed.")

    def evaluate_mutation_rules(self, target_node: str, proposed_ast: str) -> bool:
        """
        Applies Swarm Consensus Rules before mutating the AST.
        """
        if target_node not in self.semantic_graph:
            logger.warning(f"Target node {target_node} not in semantic graph.")
            return False
            
        # Check if the swarm has enough Auditors and Low Entropy
        entropy = self.scheduler.evaluate_swarm_entropy()
        auditors = sum(1 for n in self.scheduler.nodes.values() if n.role == AgentRole.AUDITOR and n.active)
        
        if entropy > 0.8 and auditors < 2:
            logger.error(f"AST Mutation Rejected: Swarm entropy too high ({entropy:.2f}) and insufficient Auditors ({auditors}).")
            return False
            
        logger.info(f"Mutation Rules Passed for {target_node}. Consensus approved.")
        return True

    def execute_ast_mutation(self, agent_id: int, target_node: str, proposed_ast: str) -> dict:
        """
        Executes the mutation using UESS invariants.
        Returns the event-sourced log artifact.
        """
        if not self.evaluate_mutation_rules(target_node, proposed_ast):
            return {"status": "rejected", "reason": "consensus_failure"}
            
        logger.info(f"Node [{agent_id}] initiated AST mutation on '{target_node}'.")
        
        # Apply the physical rewrite
        result = self.autopoiesis.mutate_function(target_node, proposed_ast)
        
        if result["status"] == "success":
            # Update Swarm State to reflect computational load and entropy spike
            self.scheduler.umap.update_control_vector(
                agent_idx=agent_id,
                queue_depth=0.0,
                error_rate=0.0,
                causal_entropy=0.8, # Entropy spikes after mutation
                cpu_load=0.9
            )
            # Rebuild graph
            self._build_semantic_graph()
            
        return result

if __name__ == "__main__":
    # Integration test with UESS Swarm Scheduler
    scheduler = UESSSwarmScheduler(capacity=10)
    
    # We will mutate a dummy file. Let's create one dynamically for the test.
    dummy_file = "dummy_target.py"
    with open(dummy_file, "w") as f:
        f.write("def compute_exergy():\n    return 42\n")
        
    engine = UESSAstMutationEngine(target_file=dummy_file, scheduler=scheduler)
    
    # Spawning an Auditor to pass consensus rules
    scheduler._spawn_node(1, AgentRole.AUDITOR, "AUDIT_AST")
    scheduler._spawn_node(2, AgentRole.AUDITOR, "AUDIT_AST_2")
    
    # Simulating a Swarm Node applying an AST Mutation Event
    new_ast = "def compute_exergy():\n    return 42 * 1.618\n"
    
    result = engine.execute_ast_mutation(agent_id=0, target_node="compute_exergy", proposed_ast=new_ast)
    logger.info(f"Mutation Result: {result}")
