/**
 * Strategy Index
 *
 * Combines all analysis strategies and provides
 * a unified analysis engine.
 */
import type { Market, MarketAnalysis, AnalysisReport, AnalysisStrategy } from "../types/index.js";
import { analyzeFundamental } from "./fundamental.js";
import { analyzeStatistical } from "./statistical.js";
import { analyzeContrarian } from "./contrarian.js";

export { analyzeFundamental } from "./fundamental.js";
export { analyzeStatistical } from "./statistical.js";
export { analyzeContrarian } from "./contrarian.js";

/**
 * Run a single strategy on a market.
 */
export function analyzeMarket(market: Market, strategy: AnalysisStrategy): MarketAnalysis {
  switch (strategy) {
    case "fundamental":
      return analyzeFundamental(market);
    case "statistical":
      return analyzeStatistical(market);
    case "contrarian":
      return analyzeContrarian(market);
  }
}

/**
 * Run all strategies on a single market and return the combined result.
 */
export function analyzeMarketAll(market: Market): MarketAnalysis[] {
  return [
    analyzeFundamental(market),
    analyzeStatistical(market),
    analyzeContrarian(market),
  ];
}

/**
 * Get the consensus analysis across all strategies.
 */
export function getConsensus(analyses: MarketAnalysis[]): MarketAnalysis | null {
  if (analyses.length === 0) return null;

  // Weight by confidence
  const totalWeight = analyses.reduce((sum, a) => sum + a.confidence, 0);
  if (totalWeight === 0) return analyses[0];

  // Count signals
  const signalCounts = { bullish: 0, bearish: 0, neutral: 0 };
  const signalWeights = { bullish: 0, bearish: 0, neutral: 0 };
  for (const a of analyses) {
    signalCounts[a.signal]++;
    signalWeights[a.signal] += a.confidence;
  }

  // Determine consensus signal
  const consensusSignal = (Object.entries(signalWeights) as [string, number][])
    .sort((a, b) => b[1] - a[1])[0][0] as "bullish" | "bearish" | "neutral";

  // Average confidence (weighted by agreement)
  const agreeingAnalyses = analyses.filter((a) => a.signal === consensusSignal);
  const avgConfidence = agreeingAnalyses.reduce((sum, a) => sum + a.confidence, 0) / agreeingAnalyses.length;

  // Boost confidence if all agree, reduce if split
  const agreement = agreeingAnalyses.length / analyses.length;
  const adjustedConfidence = avgConfidence * (0.7 + 0.3 * agreement);

  // Merge tags
  const allTags = new Set<string>();
  for (const a of analyses) {
    for (const t of a.tags) allTags.add(t);
  }

  // Combine reasoning
  const reasoning = analyses
    .map((a) => `[${a.strategy.toUpperCase()}] ${a.reasoning}`)
    .join(" ");

  // Max edge
  const maxEdge = Math.max(...analyses.map((a) => a.edge || 0));

  return {
    market: analyses[0].market,
    strategy: "fundamental", // consensus is a meta-strategy
    confidence: Math.min(95, Math.max(5, Math.round(adjustedConfidence))),
    signal: consensusSignal,
    favoredOutcome: agreeingAnalyses[0]?.favoredOutcome || analyses[0].favoredOutcome,
    reasoning,
    edge: maxEdge,
    tags: [...allTags],
  };
}

/**
 * Generate a full analysis report across all markets.
 */
export function generateReport(markets: Market[]): AnalysisReport {
  const analyses: MarketAnalysis[] = [];
  let topPick: MarketAnalysis | undefined;
  let topScore = 0;

  for (const market of markets) {
    const all = analyzeMarketAll(market);
    const consensus = getConsensus(all);
    if (consensus) {
      analyses.push(consensus);
      const score = consensus.confidence + (consensus.edge || 0);
      if (score > topScore) {
        topScore = score;
        topPick = consensus;
      }
    }
  }

  // Sort by confidence descending
  analyses.sort((a, b) => b.confidence - a.confidence);

  const summary = topPick
    ? `Top pick: "${topPick.market.question}" — ${topPick.signal} on ${topPick.favoredOutcome} (${topPick.confidence}% confidence)`
    : "No markets analyzed.";

  return {
    timestamp: new Date().toISOString(),
    markets,
    analyses,
    topPick,
    summary,
  };
}
