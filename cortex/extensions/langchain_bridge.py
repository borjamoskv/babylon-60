from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import AgentAction, AgentFinish
from cortex.engine.sync_mixin import CortexSyncEngine

class CortexLedgerCallback(BaseCallbackHandler):
    """
    O(1) Deterministic injection of LangChain agent state into Cortex-Persist.
    Generates C5-REAL cryptographic ledger entries.
    """
    def __init__(self, engine: CortexSyncEngine, agent_id: str):
        self.engine = engine
        self.agent_id = agent_id

    def on_agent_action(self, action: AgentAction, **kwargs) -> None:
        self.engine.store_fact(
            agent_id=self.agent_id,
            content=f"TOOL_CALL: {action.tool} | INPUT: {action.tool_input}",
            metadata={"log": action.log, "type": "action"}
        )

    def on_agent_finish(self, finish: AgentFinish, **kwargs) -> None:
        self.engine.store_fact(
            agent_id=self.agent_id,
            content=f"FINAL_OUTPUT: {finish.return_values}",
            metadata={"log": finish.log, "type": "finish"}
        )
