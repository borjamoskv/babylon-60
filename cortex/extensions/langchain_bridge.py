from langchain.callbacks.base import AsyncCallbackHandler
from langchain.schema import AgentAction, AgentFinish
import asyncio
import json

class CortexLedgerCallback(AsyncCallbackHandler):
    """
    O(1) Deterministic injection of LangChain agent state into Cortex-Persist.
    Generates C5-REAL cryptographic ledger entries asynchronously to prevent LEGION-10k deadlocks.
    """
    def __init__(self, engine, agent_id: str):
        self.engine = engine
        self.agent_id = agent_id

    async def on_agent_action(self, action: AgentAction, **kwargs) -> None:
        # Non-blocking telemetry injection
        payload = {"log": action.log, "type": "action"}
        asyncio.create_task(
            self.engine.store(
                agent_id=self.agent_id,
                content=f"TOOL_CALL: {action.tool} | INPUT: {action.tool_input}",
                metadata=payload
            )
        )

    async def on_agent_finish(self, finish: AgentFinish, **kwargs) -> None:
        # Serialize return_values efficiently to avoid deserialization bottlenecks
        try:
            return_str = json.dumps(finish.return_values)
        except Exception:
            return_str = str(finish.return_values)
            
        payload = {"log": finish.log, "type": "finish"}
        asyncio.create_task(
            self.engine.store(
                agent_id=self.agent_id,
                content=f"FINAL_OUTPUT: {return_str}",
                metadata=payload
            )
        )
