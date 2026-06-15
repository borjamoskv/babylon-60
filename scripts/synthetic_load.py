import asyncio
import time
import uuid
from typing import Any

from cortex.api.deps import get_async_engine
from cortex.auth import AuthResult
from cortex.engine import CortexEngine

# Payload estresor: Alta densidad de tokens con variabilidad nula (pura redundancia)
REDUNDANT_PAYLOAD = "El colapso termodinámico se evita mediante la autopoiesis del sistema. " * 50

async def inject_redundant_memory(engine: CortexEngine, index: int):
    """Inyecta un payload para saturar sqlite-vec y el analizador de redundancia."""
    try:
        fact_id = await engine.store(
            project="asi-1-lab",
            content=REDUNDANT_PAYLOAD,
            tenant_id="ouroboros-root",
            fact_type="knowledge",
            tags=["stress-test", "redundancy"],
            source="synthetic_injector",
            meta={"index": index, "entropy_target": "high"}
        )
        return fact_id
    except Exception as e:
        return e

async def main():
    print("[OUROBOROS-∞] Iniciando Torneo de Estrés Termodinámico (Capa L5)")
    print(f"[ASI-1 Lab] Inyectando redundancia semántica pura (Payload size: {len(REDUNDANT_PAYLOAD)} bytes)...")
    
    # Instanciamos el motor asíncrono
    try:
        engine = CortexEngine(db_path=":memory:", auto_embed=False)
        
        start_time = time.time()
        
        # Inyectar 1000 memorias concurrentemente
        tasks = [inject_redundant_memory(engine, i) for i in range(1000)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        
        success_count = sum(1 for r in results if isinstance(r, int))
        error_count = len(results) - success_count
        
        print("\n=== REPORTE DE EXERGÍA (BETA) ===")
        print(f"⏱️  Tiempo Total (L_i): {end_time - start_time:.2f} segundos")
        print(f"✅ Inserciones Exitosas: {success_count}")
        print(f"❌ Fallos/Rechazos (Redundancia Bloqueada): {error_count}")
        print(f"📊 Ratio de Redundancia (TK_dup): {success_count / max(1, len(tasks)):.2%}")
        
    except Exception as e:
        print(f"[FATAL] El motor colapsó bajo presión: {e}")

if __name__ == "__main__":
    asyncio.run(main())
