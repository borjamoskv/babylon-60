import asyncio
import json
from temporalio.client import Client

# Note: The client doesn't need to import the Workflow class directly if we 
# just use string names, but importing it gives type safety. We will use 
# string name to simulate a fully decoupled trigger (e.g., from FastAPI).

async def main():
    client = await Client.connect("localhost:7233")
    
    print("🚀 [CORTEX FastAPI/CLI Mock] Levantando nuevo ciclo de Insight Broker...")
    
    # 1. Start Workflow via String name (completely decoupled)
    handle = await client.start_workflow(
        "KnowledgeBrokerWorkflow",
        {"tenant_id": "nexus_2026", "telemetry_scan": True},
        id="insight-ticket-kb-0002",
        task_queue="cortex-broker-queue",
    )
    
    print(f"✅ Workflow de extracción lanzado. ID: {handle.id}")
    print("⏳ Simulando lapso de latencia humana viendo la preview (5s)...")
    await asyncio.sleep(5)
    
    print("⚡️ Recibida confirmación on-chain o webhook de Stripe. Enviando Signal a Temporal...")
    await handle.signal("confirm-payment")
    
    print("🔒 Esperando resolución termodinámica del workflow temporal...")
    result = await handle.result()
    
    print("\n==================================")
    print("🎯 RESULTADO CORTEX OBTENIDO:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("==================================\n")

if __name__ == "__main__":
    asyncio.run(main())
