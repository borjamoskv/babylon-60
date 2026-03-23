import asyncio
from temporalio.client import Client

async def main():
    client = await Client.connect("localhost:7233")
    
    print("🚀 [CORTEX OPEX-Killer Mock] Arrancando Ingestión Masiva de Telemetría (AWS/Okta)...")
    
    handle = await client.start_workflow(
        "OpexHunterWorkflow",
        "company_alpha_inc_992",
        id="opex-audit-0002",
        task_queue="cortex-broker-queue",
    )
    
    print(f"✅ Workflow de Ingestión lanzado. ID: {handle.id}")
    print("⏳ Simulando lapso de decisión del CFO debatiendo la ejecución termodinámica (15s)...")
    await asyncio.sleep(15)
    
    print("⚡️ CFO hace click en [ EXECUTE ] vía Slack. Enviando Signal a la Forja...")
    await handle.signal("approve-opex-purge")
    
    print("🔒 Esperando ejecución de la purga y receipt de Stripe...")
    result = await handle.result()
    
    print("\n==================================")
    print("🎯 RESOLUCIÓN OPEX FINALIZADA:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    print("==================================\n")

if __name__ == "__main__":
    asyncio.run(main())
