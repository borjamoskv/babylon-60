import asyncio
import aiohttp
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("anergy_injector")

# Target CORTEX facts endpoint
TARGET_URL = "http://127.0.0.1:8000/v1/facts"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer ctx_4d82d96824bbde0e49dc176e34a1c09df9387f7f5bfedddaf936a072627b165c"
}

# Base phrase to mutate slightly (forces high cosine similarity computation)
BASE_PHRASE = "El núcleo de MOSKV-1 opera con entropía controlada."

async def inject_redundant_fact(session: aiohttp.ClientSession, worker_id: int, request_id: int):
    # Minor mutation to avoid pure hash collision and force vector similarity calculation
    payload = {
        "project": "anergy_stress_test",
        "content": f"{BASE_PHRASE} [Variación {worker_id}-{request_id}]",
        "fact_type": "knowledge",
        "tags": ["stress", "redundancy"],
        "source": "anergy_injector",
        "meta": {
            "is_synthetic": True,
            "CORTEX-TAINT": f"taint:anergy_bot:session_0:{time.time()}:fake_sha3"
        }
    }
    
    start_time = time.perf_counter()
    try:
        async with session.post(TARGET_URL, json=payload, headers=HEADERS) as response:
            status = response.status
            # Read text to ensure full response is downloaded
            await response.text()
            latency = time.perf_counter() - start_time
            return status, latency
    except Exception as e:
        return 500, time.perf_counter() - start_time

async def swarm_attack(total_requests: int, concurrency: int):
    logger.info(f"Iniciando ataque de anergía masiva: {total_requests} requests @ {concurrency} concurrencia.")
    
    connector = aiohttp.TCPConnector(limit=concurrency)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for i in range(total_requests):
            tasks.append(inject_redundant_fact(session, worker_id=i % concurrency, request_id=i))
        
        results = await asyncio.gather(*tasks)
        
        status_codes = [r[0] for r in results]
        latencies = [r[1] for r in results]
        
        # Count status occurrences
        counts = {}
        for code in status_codes:
            counts[code] = counts.get(code, 0) + 1
            
        logger.info("=== Resultados del Ataque ===")
        for code, count in sorted(counts.items()):
            logger.info(f"Código HTTP {code}: {count}")
            
        if latencies:
            logger.info(f"Latencia Media: {sum(latencies)/len(latencies):.4f}s")
            logger.info(f"Latencia Max: {max(latencies):.4f}s")

if __name__ == "__main__":
    # Inyectar 1000 hechos con 50 de concurrencia para pruebas iniciales, luego podemos escalar
    asyncio.run(swarm_attack(total_requests=1000, concurrency=50))
