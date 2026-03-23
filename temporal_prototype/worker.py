import asyncio
from datetime import timedelta
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker

# Activities (Non-deterministic operations: DB, I/O)
@activity.defn
async def detect_pattern_activity(data: dict) -> str:
    print(f"[Activity] Detectando patrón causal en: {data}")
    await asyncio.sleep(1) # Simulación db scan
    return "MEMORY_LEAK_IN_LIBA_V2_CAUSING_15G_EXTRA_RAM"

@activity.defn
async def validate_insight_activity(pattern: str) -> bool:
    print(f"[Activity] CORTEX Guards evaluando (immune gate): {pattern}")
    return True # Es válido

@activity.defn
async def generate_preview_activity(pattern: str) -> str:
    print("[Activity] Emiendo draft y criptograma al Ledger.")
    return f"PREF: Encontramos la causa de un leak que traga 15GB. Pay $50 para fix."

@activity.defn
async def unlock_insight_activity(pattern: str) -> str:
    print("[Activity] Emietendo resolución total de la exergía al cliente.")
    return f"SOLUCIÓN CORTEX: Actualiza libA a v2.1.0 y reinicia cache. ({pattern})"

# Workflow (Deterministic Orchestration)
@workflow.defn
class KnowledgeBrokerWorkflow:
    def __init__(self) -> None:
        # Estado interno reentrante
        self.payment_received = False
        self.aborted = False

    @workflow.run
    async def run(self, input_data: dict) -> dict:
        # 1. Detect Pattern
        pattern = await workflow.execute_activity(
            detect_pattern_activity, input_data, start_to_close_timeout=timedelta(minutes=1)
        )
        
        # 2. Validate
        is_valid = await workflow.execute_activity(
            validate_insight_activity, pattern, start_to_close_timeout=timedelta(minutes=1)
        )
        
        if not is_valid:
            return {"status": "rejected_by_guards"}
            
        # 3. Generate Preview
        preview = await workflow.execute_activity(
            generate_preview_activity, pattern, start_to_close_timeout=timedelta(minutes=1)
        )
        
        workflow.logger.info(f"WORKFLOW SUSPENDIDO. Esperando pago para: {preview}")
        
        # 4. Await Payment (Signal)
        # Aquí el Worker puede morir / apagarse. 
        # Si pasan 3 meses y se vuelve a encender, el wait retoma.
        await workflow.wait_condition(
            lambda: self.payment_received or self.aborted
        )

        if self.aborted:
             return {"status": "aborted", "insight": "N/A"}

        # 5. Unlock (Después de la señal)
        insight = await workflow.execute_activity(
            unlock_insight_activity, pattern, start_to_close_timeout=timedelta(minutes=1)
        )

        return {"status": "success", "insight": insight}

    @workflow.signal(name="confirm-payment")
    async def confirm_payment_signal(self) -> None:
        self.payment_received = True

    @workflow.signal(name="abort-insight")
    async def abort_insight_signal(self) -> None:
        self.aborted = True

async def main():
    # El worker del cliente "CORTEX"
    client = await Client.connect("localhost:7233")
    
    worker = Worker(
        client,
        task_queue="cortex-insights-queue",
        workflows=[KnowledgeBrokerWorkflow],
        activities=[detect_pattern_activity, validate_insight_activity, generate_preview_activity, unlock_insight_activity]
    )
    print("-> Worker de CORTEX inicializado en temporalite loop. Escuchando `cortex-insights-queue`.")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
