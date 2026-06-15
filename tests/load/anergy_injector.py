import asyncio
import aiohttp
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("anergy_injector")

# Target CORTEX memory endpoint
TARGET_URL = "http://127.0.0.1:8000/api/v1/memory/insert"
HEADERS = {"Content-Type": "application/json", "X-Tenant-ID": "test-tenant-1"}

# Base phrase to mutate slightly (forces high cosine similarity computation)
BASE_PHRASE = "El núcleo de MOSKV-1 opera con entropía controlada."

async def inject_redundant_fact(session: aiohttp.ClientSession, worker_id: int, request_id: int):
    # Minor mutation to avoid pure hash collision and force vector similarity calculation
    payload = {
        "content": f"{BASE_PHRASE} [Variación {worker_id}-{request_id}]",
        "metadata": {
            "source": "anergy_injector",
            "is_synthetic": True,
            "CORTEX-TAINT": f"taint:anergy_bot:session_0:{time.time()}:fake_sha3"
        }
    }
    
    start_time = time.perf_counter()
    try:
        async with session.post(TARGET_URL, json=payload, headers=HEADERS) as response:
            status = response.status
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
        
        logger.info("=== Resultados del Ataque ===")
        logger.info(f"Éxitos (200): {status_codes.count(200)}")
        logger.info(f"Rechazos/Locks (429/500): {len(status_codes) - status_codes.count(200)}")
        if latencies:
            logger.info(f"Latencia Media: {sum(latencies)/len(latencies):.4f}s")
            logger.info(f"Latencia Max: {max(latencies):.4f}s")

if __name__ == "__main__":
    # Inyectar 10,000 hechos con 200 de concurrencia
    asyncio.run(swarm_attack(total_requests=10000, concurrency=200))
