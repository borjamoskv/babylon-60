import { BaseCallbackHandler } from "@langchain/core/callbacks/base";
import { CortexClient, CortexClientOptions } from "cortex-persist";

export class CortexCallbackHandler extends BaseCallbackHandler {
    name = "CortexCallbackHandler";
    private client: CortexClient;

    constructor(options: CortexClientOptions) {
        super();
        this.client = new CortexClient(options);
    }

    async handleLLMStart(llm: any, prompts: string[], runId: string) {
        await this.client.logEvent({
            type: "agent.llm_start",
            actor: "langchain-agent",
            payload: { runId, prompts }
        });
    }

    async handleLLMError(err: Error, runId: string) {
        await this.client.logEvent({
            type: "agent.llm_error",
            actor: "langchain-agent",
            payload: { runId, error: err.message }
        });
    }

    async handleChainStart(chain: any, inputs: Record<string, any>, runId: string) {
        await this.client.logEvent({
            type: "agent.chain_start",
            actor: "langchain-agent",
            payload: { runId, inputs }
        });
    }

    async handleToolStart(tool: any, input: string, runId: string) {
        await this.client.logEvent({
            type: "agent.tool_start",
            actor: "langchain-agent",
            payload: { runId, tool: tool?.name, input }
        });
    }
}
