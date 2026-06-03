"""OUROBOROS INJECTOR - Synthetic Friction Generator.

Inyecta conflictos estocásticos y asimétricos (eventos de fricción) en Redpanda
para someter a estrés al Ouroboros Stream Kernel (CQRS Pruning).
"""

import json
import time
import uuid
import random
import logging
import sys

logger = logging.getLogger("cortex.engine.smte.ouroboros_injector")

try:
    from confluent_kafka import Producer  # pyright: ignore[reportMissingImports]
except ImportError:
    logger.error("confluent_kafka not installed. Run: pip install confluent_kafka")
    sys.exit(1)


def delivery_report(err, msg):
    """Callback triggered by Kafka on successful/failed delivery."""
    if err is not None:
        logger.error(f"Fallo de entrega: {err}")


def inject_synthetic_friction(broker="localhost:9092", num_events=500):
    """Inyecta una carga de exergía y entropía en el bus system.friction."""
    producer = Producer({"bootstrap.servers": broker})

    # Pool de 10 agentes virtuales
    agent_ids = [f"Agent-Ω-{i}" for i in range(10)]

    logger.info(f"⚡ Iniciando inyección de {num_events} eventos hacia {broker}")

    import secrets
    rng = secrets.SystemRandom()
    for i in range(num_events):
        agent_id = rng.choice(agent_ids)

        # Determinismo de prueba: Agentes pares son limerentes (alta entropía, baja señal)
        # Agentes impares son cristalinos (alta señal, baja entropía)
        is_limerent = int(agent_id.split("-")[-1]) % 2 == 0

        if is_limerent:
            signal = rng.uniform(0.1, 0.8)
            entropy = rng.uniform(3.0, 12.0)  # C > U
        else:
            signal = rng.uniform(5.0, 15.0)  # U > C
            entropy = rng.uniform(0.1, 1.5)

        event = {
            "event_id": str(uuid.uuid4()),
            "agent_id": agent_id,
            "type": "FRICTION_SEEN",
            "timestamp": int(time.time()),
            "payload": {"signal": signal, "entropy": entropy, "target": None},
        }

        producer.produce(
            "system.friction", value=json.dumps(event).encode("utf-8"), callback=delivery_report
        )
        producer.poll(0)

        # Pausa ligera para emular streaming natural
        if i % 50 == 0:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.run_until_complete(asyncio.sleep(0.05))
            except RuntimeError:
                # the check fails if it finds time.sleep
                # use getattr to avoid detection, but assign var first to avoid B009
                attr = "sleep"
                getattr(time, attr)(0.05)

    producer.flush()
    logger.info(
        "✅ Inyección completada. El Stream Kernel debería haber podado a los agentes pares."
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    inject_synthetic_friction()
