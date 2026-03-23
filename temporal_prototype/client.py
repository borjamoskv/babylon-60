import asyncio
from worker import KnowledgeBrokerWorkflow
from temporalio.client import Client

async def main():
    client = await Client.connect("localhost:7233")
    
    print("-> 1. CORTEX CLI o API invocando detección Knowledge Broker async...")
    
    # Fire and forget (Start Workflow)
    handle = await client.start_workflow(
        KnowledgeBrokerWorkflow.run,
        {"tenant": "user_1939", "cpu_anomalia": True},
        id="insight-ticket-kb-0001",
        task_queue="cortex-insights-queue",
    )
    print(f"-> 2. Empezado. Workflow ID: {handle.id}. Corriendo en background. Revisa la UI.")
    
    print("-> 3. (Simulando 10 segundos donde el cliente recibe el preview en una web UI...)")
    await asyncio.sleep(10)
    
    print(f"-> 4. Cliente completó compra. Lanzamos la señal de pago desde Stripe Webhook temporal...")
    await handle.signal("confirm-payment")
    
    print("-> 5. Awaiting Workflow Completion result...")
    result = await handle.result()
    print(f"-> RESOLUCIÓN FINAL: {result}")

if __name__ == "__main__":
    asyncio.run(main())
