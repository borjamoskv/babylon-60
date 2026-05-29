import ast
import logging
from cortex.engine.smte.parser import AgentASTParser
from cortex.engine.smte.llm_mutator import llm_driven_mutator
from cortex.guards.exergy_guard import calculate_exergy

logger = logging.getLogger("cortex.engine.smte.trigger")
logging.basicConfig(level=logging.INFO)

def run_mutation_cycle(target_path: str):
    parser = AgentASTParser(target_path)
    
    initial_exergy = calculate_exergy(parser.source_code)
    logger.info(f"[*] Initial Exergy of {target_path}: {initial_exergy:.4f}")
    
    logger.info("[*] Applying LLM-Driven AST Mutation...")
    if llm_driven_mutator(parser):
        logger.info("[*] Mutation structurally sound. Crystallizing...")
        new_source = parser.crystallize()
        new_exergy = calculate_exergy(new_source)
        logger.info(f"[*] New Exergy: {new_exergy:.4f}")
        
        if new_exergy >= initial_exergy:
            logger.info("[+] Mutation ACCEPTED. Fitness improved or maintained.")
        else:
            logger.warning("[-] Mutation DEGRADED exergy, but committed for testing purposes.")
    else:
        logger.error("[-] Mutation structural check failed.")

if __name__ == "__main__":
    target = "cortex/engine/smte/__init__.py"
    run_mutation_cycle(target)
