import asyncio
import time

from cortex.graph.engine import detect_relationships, extract_entities


async def run_stress_test():
    print("⚡ INICIANDO PRUEBA DE ESTRÉS: VECTOR EUSKADI ⚡\n")

    # Base facts with heavy Basque declensions
    base_facts = [
        "Cortex-ek SQLite-ekin lan egiten du.",  # SQLite -> uses
        "Sistema Docker-ra deploiatzen da.",  # Docker -> deployed_to
        "Python-tik datorren logika.",  # Python -> extends
        "Next.js-ko osagaiak errendatzen ditu.",  # Next.js -> related_to
        "Anthropic-k sortua eta balioztatua.",  # Anthropic -> created_by
    ]

    # Multiply to simulate a heavy workload (100,000 facts)
    corpus = base_facts * 20000

    print(f"[*] Corpus generado: {len(corpus)} hechos sintéticos.")
    print("[*] Ejecutando Demultiplexor O(1) en 1 hilo (Worst Case Scenario)...\n")

    start_time = time.time()

    total_entities = 0
    total_relations = 0

    for fact in corpus:
        entities = extract_entities(fact)
        relations = detect_relationships(fact, entities)
        total_entities += len(entities)
        total_relations += len(relations)

    cpu_end = time.time()
    elapsed = cpu_end - start_time

    print("📊 RESULTADOS DE EXERGÍA (Ω₂)")
    print("-----------------------------")
    print(f"Tiempo Total (CPU) : {elapsed:.4f} segundos")
    print(f"Entidades Extraídas: {total_entities}")
    print(f"Aristas Generadas  : {total_relations}")
    print(f"Rendimiento (TPS)  : {len(corpus) / elapsed:.0f} hechos/segundo")
    print("-----------------------------")

    if elapsed < 5.0:
        print("\n✅ PRUEBA SUPERADA: Umbral de Singularidad mantenido.")
    else:
        print("\n⚠️ ALERTA: Fricción termodinámica detectada.")


if __name__ == "__main__":
    asyncio.run(run_stress_test())
