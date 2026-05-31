import asyncio
import sys

sys.path.append("cortex-core")
from persistence.security_recon import SecurityReconDaemon
from persistence.ledger import LedgerManager


async def run_recon():
    ledger = LedgerManager()
    SecurityReconDaemon(ledger)
    print("Initiating SecurityReconDaemon single pass...")
    # Just enqueue one task
    import persistence.outbox as outbox

    payload = {
        "type": "RESEARCH_SOTA_IA_AGENTS",
        "target": "agente-sota",
        "reward": 15.0,
        "description": "Continuous SOTA AI agents investigation. Extract exergy voids and evaluate empirical results from agentic architectures.",
    }
    outbox.enqueue_swarm_task("SAGE_COUNCIL", payload)
    print("Task Enqueued successfully. Recon pass complete.")


if __name__ == "__main__":
    asyncio.run(run_recon())
