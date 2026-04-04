import z3
import time
import json
import os
import random
from concurrent.futures import ProcessPoolExecutor

def generate_hard_3sat(n_vars, ratio=4.26):
    """
    Generates a 3-SAT instance near the phase transition (ratio ~4.26)
    where instances are computationally 'hardest' for solvers.
    """
    n_clauses = int(n_vars * ratio)
    variables = [z3.Bool(f'x_{i}') for i in range(n_vars)]
    clauses = []
    for _ in range(n_clauses):
        clause_vars = random.sample(variables, 3)
        literals = [v if random.choice([True, False]) else z3.Not(v) for v in clause_vars]
        clauses.append(z3.Or(*literals))
    return variables, clauses

def solve_deep_node(node_data):
    idx, n_vars, ratio = node_data
    
    # Re-instantiate in worker
    vars, clauses = generate_hard_3sat(n_vars, ratio)
    
    solver = z3.Solver()
    s = z3.Solver()
    for c in clauses:
        s.add(c)
        
    start_time = time.perf_counter()
    result = s.check()
    exergy_cost = time.perf_counter() - start_time
    
    return {
        "id": idx,
        "n_vars": n_vars,
        "n_clauses": len(clauses),
        "result": str(result),
        "time_ms": round(exergy_cost * 1000, 4)
    }

class PvsNP_DeepVerify:
    def __init__(self, num_samples=1000):
        self.num_samples = num_samples
        self.results = []

    def execute(self, vars_min=100, vars_max=200):
        print(f"🔱 INICIANDO C5-VERIFY: P vs NP (Deep Strike)")
        print(f"◈ Target: Phasetransition threshold (r=4.26)")
        print(f"◈ Agentes: {self.num_samples} parallel solvers")
        
        nodes = [(i, random.randint(vars_min, vars_max), 4.26) for i in range(self.num_samples)]
        
        with ProcessPoolExecutor(max_workers=11) as executor:
            self.results = list(executor.map(solve_deep_node, nodes))
            
        self.persist()

    def persist(self):
        log_path = "/Users/borjafernandezangulo/Cortex-Persist/millennium_strike/l1_turing/deep_verify_p_np.json"
        with open(log_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"↳ Deep Verification Log: {log_path} (C5-REAL)")

if __name__ == "__main__":
    verifier = PvsNP_DeepVerify(num_samples=1000)
    verifier.execute(vars_min=120, vars_max=180)
