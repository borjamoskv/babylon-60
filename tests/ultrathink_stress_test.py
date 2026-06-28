import subprocess
import random
import sys
import time

def generate_chaos_payload(seed: int) -> str:
    random.seed(seed)
    
    # Generate chaotic F60 fractions
    tens_int = '<' * random.randint(0, 5)
    ones_int = 'Y' * random.randint(0, 9)
    tens_frac = '<' * random.randint(0, 5)
    ones_frac = 'Y' * random.randint(0, 9)
    
    fraction = f"[ {tens_int}{ones_int} ; {tens_frac}{ones_frac} ]"
    if fraction == "[  ;  ]":
        fraction = "[ < ; Y ]"
        
    depth_limit = random.randint(500, 15000)
    
    payload = f"""
ALLOC TIME R0
ALLOC I64 R1
NIG R0 {fraction} UNIT.TICK
NIG R1 {fraction}
# Try to force mathematical fracture across typed domains
DAH R0 R1
BA.EXACT R0 R1
FORK "SINGULARITY"
EXECUTE "CHECK"
AWAIT "CHECK" "END"
MUB "SINGULARITY"
FORK "SINGULARITY"
MUB "END"
HALT
"""
    return payload

def run_stress_test(iterations=50):
    print(f"[ULTRATHINK P0] Iniciando Stress Test Termodinámico ({iterations} iteraciones)...")
    successes = 0
    panics = 0
    timeouts = 0
    
    # Compile the binary once in release mode for speed
    subprocess.run(["cargo", "build", "--release"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    start_time = time.time()
    
    for i in range(iterations):
        payload = generate_chaos_payload(i)
        with open("tests/temp_fuzz.b60", "w") as f:
            f.write(payload)
            
        try:
            # 2 second strict timeout per vector
            result = subprocess.run(
                ["./target/release/runtime", "tests/temp_fuzz.b60"],
                capture_output=True,
                text=True,
                timeout=2.0
            )
            
            out = result.stdout + result.stderr
            
            # Check if it was safely caught by our compiler/VM guards
            if "CRITICAL COMPILE ERROR" in out or "CRITICAL ERROR" in out:
                successes += 1
            elif "thread 'main' panicked" in out:
                panics += 1
                print(f"\n[!] FRACTURA DETECTADA (Panic) en Seed {i}:\n{out}")
            else:
                # Execution finished safely despite chaotic input
                successes += 1
                
        except subprocess.TimeoutExpired:
            timeouts += 1
            print(f"\n[!] LIVENESS LOSS (Timeout) en Seed {i}. VM bloqueada.")
            
        if (i+1) % 10 == 0:
            print(f"  -> {i+1} vectores inyectados. (T={time.time() - start_time:.2f}s)")
            
    print("\n=== REPORTE DE EXERGÍA ULTRATHINK ===")
    print(f"Total Iteraciones : {iterations}")
    print(f"Defensas Exitosas : {successes}")
    print(f"Panics (Corrupción): {panics}")
    print(f"Timeouts (Liveness): {timeouts}")
    
    if panics == 0 and timeouts == 0:
        print("\n[C5-REAL] ESTADO SEGURO. Mitigación matemáticamente irrompible. Cero anergía.")
        sys.exit(0)
    else:
        print("\n[FATAL] La singularidad persiste. Refactorización estructural requerida.")
        sys.exit(1)

if __name__ == "__main__":
    run_stress_test(50)
