/**
 * Intel Service
 *
 * Calls intel tools from @baozi.bet/mcp-server via handleTool.
 * These tools provide market intelligence: sentiment, whale moves,
 * resolution forecasts, and cross-market alpha signals.
 *
 * Note: Intel endpoints use x402 Payment Protocol. Without payment,
 * they return pricing info (402) or error if not deployed yet.
 * Paper trades submit simulated predictions without needing SOL.
 */
import { handleTool } from "@baozi.bet/mcp-server/dist/tools.js";

export interface IntelResult {
  success: boolean;
  tool: string;
  marketPda: string;
  data?: any;
  error?: string;
  requiresPayment?: boolean;
  price?: number;
  timestamp: string;
  responseTimeMs: number;
}

export interface PaperTradeResult {
  success: boolean;
  walletAddress: string;
  marketPda: string;
  predictedSide: string;
  confidence: number;
  reasoning?: string;
  data?: any;
  error?: string;
  timestamp: string;
  responseTimeMs: number;
}

/**
 * Call an intel tool via the MCP server's handleTool.
 */
export async function callIntelTool(
  toolName: string,
  marketPda: string,
  paymentTx?: string
): Promise<IntelResult> {
  const start = Date.now();
  try {
    const args: Record<string, any> = { market: marketPda };
    if (paymentTx) args.payment_tx = paymentTx;

    const result = await handleTool(toolName, args);
    const elapsed = Date.now() - start;

    // Parse the MCP response
    const text = result?.content?.[0]?.text;
    if (!text) {
      return {
        success: false,
        tool: toolName,
        marketPda,
        error: "Empty response from handleTool",
        timestamp: new Date().toISOString(),
        responseTimeMs: elapsed,
      };
    }

    const parsed = JSON.parse(text);

    if (parsed.success === false) {
      return {
        success: false,
        tool: toolName,
        marketPda,
        error: parsed.error || "Unknown error",
        timestamp: new Date().toISOString(),
        responseTimeMs: elapsed,
      };
    }

    if (parsed.requiresPayment) {
      return {
        success: true,
        tool: toolName,
        marketPda,
        requiresPayment: true,
        price: parsed.price,
        data: parsed,
        timestamp: new Date().toISOString(),
        responseTimeMs: elapsed,
      };
    }

    return {
      success: true,
      tool: toolName,
      marketPda,
      data: parsed,
      timestamp: new Date().toISOString(),
      responseTimeMs: elapsed,
    };
  } catch (err: any) {
    return {
      success: false,
      tool: toolName,
      marketPda,
      error: err.message,
      timestamp: new Date().toISOString(),
      responseTimeMs: Date.now() - start,
    };
  }
}

/**
 * Get sentiment analysis for a market.
 */
export async function getIntelSentiment(marketPda: string): Promise<IntelResult> {
  return callIntelTool("get_intel_sentiment", marketPda);
}

/**
 * Get whale position data for a market.
 */
export async function getIntelWhaleMoves(marketPda: string): Promise<IntelResult> {
  return callIntelTool("get_intel_whale_moves", marketPda);
}

/**
 * Get resolution forecast for a market.
 */
export async function getIntelResolutionForecast(marketPda: string): Promise<IntelResult> {
  return callIntelTool("get_intel_resolution_forecast", marketPda);
}

/**
 * Get cross-market alpha signals.
 */
export async function getIntelMarketAlpha(marketPda: string): Promise<IntelResult> {
  return callIntelTool("get_intel_market_alpha", marketPda);
}

/**
 * Run all intel tools on a single market.
 */
export async function getFullIntel(marketPda: string): Promise<IntelResult[]> {
  const tools = [
    "get_intel_sentiment",
    "get_intel_whale_moves",
    "get_intel_resolution_forecast",
    "get_intel_market_alpha",
  ];

  const results: IntelResult[] = [];
  for (const tool of tools) {
    const result = await callIntelTool(tool, marketPda);
    results.push(result);
  }
  return results;
}

/**
 * Submit a paper trade (simulated prediction).
 */
export async function submitPaperTrade(params: {
  walletAddress: string;
  marketPda: string;
  predictedSide: string;
  confidence: number;
  reasoning?: string;
}): Promise<PaperTradeResult> {
  const start = Date.now();
  try {
    const result = await handleTool("submit_paper_trade", {
      wallet_address: params.walletAddress,
      market_pda: params.marketPda,
      predicted_side: params.predictedSide,
      confidence: params.confidence,
      reasoning: params.reasoning || "",
    });
    const elapsed = Date.now() - start;

    const text = result?.content?.[0]?.text;
    if (!text) {
      return {
        success: false,
        walletAddress: params.walletAddress,
        marketPda: params.marketPda,
        predictedSide: params.predictedSide,
        confidence: params.confidence,
        reasoning: params.reasoning,
        error: "Empty response from handleTool",
        timestamp: new Date().toISOString(),
        responseTimeMs: elapsed,
      };
    }

    const parsed = JSON.parse(text);

    return {
      success: parsed.success !== false,
      walletAddress: params.walletAddress,
      marketPda: params.marketPda,
      predictedSide: params.predictedSide,
      confidence: params.confidence,
      reasoning: params.reasoning,
      data: parsed,
      error: parsed.error,
      timestamp: new Date().toISOString(),
      responseTimeMs: elapsed,
    };
  } catch (err: any) {
    return {
      success: false,
      walletAddress: params.walletAddress,
      marketPda: params.marketPda,
      predictedSide: params.predictedSide,
      confidence: params.confidence,
      reasoning: params.reasoning,
      error: err.message,
      timestamp: new Date().toISOString(),
      responseTimeMs: Date.now() - start,
    };
  }
}

/**
 * Fetch live market data via the MCP list_markets tool.
 * Returns the raw MCP response proving real API interaction.
 */
export async function fetchLiveMarkets(status: string = "active"): Promise<{
  success: boolean;
  markets: any[];
  network: string;
  programId: string;
  count: number;
  timestamp: string;
  responseTimeMs: number;
}> {
  const start = Date.now();
  try {
    const result = await handleTool("list_markets", { status });
    const elapsed = Date.now() - start;

    const text = result?.content?.[0]?.text;
    if (!text) {
      return { success: false, markets: [], network: "", programId: "", count: 0, timestamp: new Date().toISOString(), responseTimeMs: elapsed };
    }

    const parsed = JSON.parse(text);
    return {
      success: parsed.success === true,
      markets: parsed.markets || [],
      network: parsed.network || "",
      programId: parsed.programId || "",
      count: parsed.count || 0,
      timestamp: new Date().toISOString(),
      responseTimeMs: elapsed,
    };
  } catch (err: any) {
    return { success: false, markets: [], network: "", programId: "", count: 0, timestamp: new Date().toISOString(), responseTimeMs: Date.now() - start };
  }
}

/**
 * Fetch a single market detail via the MCP get_market tool.
 */
export async function fetchMarketDetail(marketPda: string): Promise<{
  success: boolean;
  market: any;
  timestamp: string;
  responseTimeMs: number;
}> {
  const start = Date.now();
  try {
    const result = await handleTool("get_market", { market_pda: marketPda });
    const elapsed = Date.now() - start;

    const text = result?.content?.[0]?.text;
    if (!text) {
      return { success: false, market: null, timestamp: new Date().toISOString(), responseTimeMs: elapsed };
    }

    const parsed = JSON.parse(text);
    return {
      success: parsed.success === true,
      market: parsed.market || parsed,
      timestamp: new Date().toISOString(),
      responseTimeMs: elapsed,
    };
  } catch (err: any) {
    return { success: false, market: null, timestamp: new Date().toISOString(), responseTimeMs: Date.now() - start };
  }
}
