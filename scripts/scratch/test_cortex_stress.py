import asyncio
import logging
from unittest.mock import patch

from cortex.engine.heartbeat import HeartbeatEmitter, SwarmProcessRegistry, safe_browser_execution

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(message)s")


class MockBrowser:
    def __init__(self, id):
        self.id = id
        self.is_closed = False

    async def close(self):
        logging.info(f"🛡️ [MockBrowser {self.id}] Aniquilado exitosamente por el Registry.")
        self.is_closed = True


async def agent_task(browser_id):
    browser = MockBrowser(browser_id)
    try:
        async with safe_browser_execution(browser):
            logging.info(f"🌐 [Agente {browser_id}] Navegador instanciado y registrado.")
            await asyncio.sleep(10)  # Simula un trabajo largo
    except asyncio.CancelledError:
        pass


class MockNexus:
    async def mutate(self, *args, **kwargs):
        return True


async def main():
    print("\n" + "=" * 60)
    print(" INICIANDO CORTEX STRESS TEST (Simulación de Presión RAM)")
    print("=" * 60 + "\n")

    # 1. Spawn 5 "Agents" with mock browsers
    tasks = []
    for i in range(1, 6):
        tasks.append(asyncio.create_task(agent_task(i)))

    await asyncio.sleep(0.2)  # Give them time to register

    print("\n--- ESTADO DEL REGISTRO ANTES DEL HEARTBEAT ---")
    print(
        f"Navegadores activos en SwarmProcessRegistry: {len(SwarmProcessRegistry._active_browsers)}\n"
    )

    # 2. Setup Heartbeat
    nexus = MockNexus()
    hb = HeartbeatEmitter(nexus=nexus, engine=None, project="CORTEX_STRESS_TEST")

    # 3. Pulse Heartbeat with mocked hygiene returning 85% memory pressure
    print("--- 🔴 DETONANDO PULSO DE HEARTBEAT (MEMORIA AL 85%) ---\n")
    with patch("cortex.utils.hygiene.check_system_health", return_value={"memory_pressure": 0.85}):
        # Mockeamos strike_fix_purge para que no mate procesos reales del sistema durante el test
        with patch("cortex.utils.hygiene.strike_fix_purge"):
            await hb.pulse()

    await asyncio.sleep(0.5)  # Allow background tasks to complete

    # 4. Verify that browsers were closed
    print("\n--- ESTADO DEL REGISTRO TRAS EL PURGE ---")
    print(
        f"Navegadores activos en SwarmProcessRegistry: {len(SwarmProcessRegistry._active_browsers)}"
    )
    print("=" * 60 + "\n")

    for task in tasks:
        task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
