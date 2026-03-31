/**
 * Statistical Analysis Strategy
 *
 * Analyzes odds from a purely numerical perspective:
 * pool distribution, implied returns, Kelly criterion sizing,
 * and market efficiency metrics.
 */
import type { Market, MarketAnalysis } from "../types/index.js";
import { formatSol, formatPercent } from "../utils/helpers.js";

export function analyzeStatistical(market: Market): MarketAnalysis {
  const tags: string[] = ["statistical"];
  const factors: string[] = [];
  let confidence = 50;
  let signal: "bullish" | "bearish" | "neutral" = "neutral";
  let favoredOutcome = market.outcomes[0]?.label || "Yes";
  let edge = 0;

  const totalPool = market.pool.total;

  // 1. Implied probability analysis
  const probs = market.outcomes.map((o) => o.probability);
  const probSum = probs.reduce((a, b) => a + b, 0);

  // Check if probabilities are well-calibrated (should sum to ~1.0)
  if (Math.abs(probSum - 1.0) > 0.05) {
    factors.push(`Probability sum ${formatPercent(probSum)} — market may have pricing anomaly`);
    tags.push("anomaly");
    confidence += 5;
  }

  // 2. Implied returns for each outcome
  const returns = market.outcomes.map((o) => {
    if (o.pool <= 0 || totalPool <= 0) return Infinity;
    return totalPool / o.pool;
  });

  const bestReturn = Math.max(...returns.filter((r) => r !== Infinity));
  const bestReturnIdx = returns.indexOf(bestReturn);
  const bestOutcome = market.outcomes[bestReturnIdx];

  if (bestReturn > 5) {
    factors.push(
      `${bestOutcome?.label} has ${bestReturn.toFixed(1)}x implied return — longshot`
    );
    tags.push("longshot");
  } else if (bestReturn > 2) {
    factors.push(
      `${bestOutcome?.label} has ${bestReturn.toFixed(1)}x implied return`
    );
  }

  // 3. Pool concentration (HHI-like metric)
  const poolShares = market.outcomes.map((o) =>
    totalPool > 0 ? o.pool / totalPool : 1 / market.outcomes.length
  );
  const hhi = poolShares.reduce((sum, s) => sum + s * s, 0);
  const normalizedHhi = (hhi - 1 / market.outcomes.length) / (1 - 1 / market.outcomes.length);

  if (normalizedHhi > 0.5) {
    factors.push(
      `High pool concentration (HHI ${normalizedHhi.toFixed(2)}) — one side dominates`
    );
    tags.push("concentrated");

    // Find the dominant side
    const dominant = market.outcomes.reduce((a, b) => (a.pool > b.pool ? a : b));
    signal = dominant.index === 0 ? "bullish" : "bearish";
    favoredOutcome = dominant.label;
    confidence += 5;
  } else if (normalizedHhi < 0.1) {
    factors.push(
      `Even pool distribution (HHI ${normalizedHhi.toFixed(2)}) — genuine uncertainty`
    );
    tags.push("balanced");
    confidence -= 5;
  }

  // 4. Kelly Criterion analysis (for binary markets)
  if (market.outcomes.length === 2) {
    const p = market.outcomes[0].probability; // market-implied probability
    const q = 1 - p;
    const b = totalPool > 0 ? (totalPool - market.outcomes[0].pool) / market.outcomes[0].pool : 1;

    // Kelly fraction: f = (bp - q) / b
    const kellyYes = b > 0 ? (b * p - q) / b : 0;
    const bNo = totalPool > 0 ? (totalPool - market.outcomes[1].pool) / market.outcomes[1].pool : 1;
    const kellyNo = bNo > 0 ? (bNo * q - p) / bNo : 0;

    if (kellyYes > 0.1) {
      factors.push(`Kelly suggests ${formatPercent(kellyYes)} of bankroll on Yes`);
      signal = "bullish";
      favoredOutcome = market.outcomes[0].label;
      confidence += 10;
    } else if (kellyNo > 0.1) {
      factors.push(`Kelly suggests ${formatPercent(kellyNo)} of bankroll on No`);
      signal = "bearish";
      favoredOutcome = market.outcomes[1].label;
      confidence += 10;
    } else {
      factors.push("Kelly suggests no strong edge on either side");
    }
  }

  // 5. Volume-weighted confidence
  if (totalPool >= 10) {
    factors.push(`Pool ${formatSol(totalPool)} — statistically significant pricing`);
    confidence += 10;
  } else if (totalPool >= 1) {
    factors.push(`Pool ${formatSol(totalPool)} — moderate confidence in pricing`);
    confidence += 5;
  } else if (totalPool > 0) {
    factors.push(`Pool ${formatSol(totalPool)} — pricing may not reflect true odds`);
    confidence -= 10;
  }

  // 6. Detect potential value bets (outcomes with pool share << implied probability)
  for (const outcome of market.outcomes) {
    const poolShare = totalPool > 0 ? outcome.pool / totalPool : 0;
    if (outcome.probability > 0.3 && poolShare < outcome.probability * 0.5 && totalPool > 0.5) {
      factors.push(
        `Potential value: ${outcome.label} at ${formatPercent(poolShare)} pool share but ${formatPercent(outcome.probability)} implied probability`
      );
      tags.push("value-bet");
      edge = (outcome.probability - poolShare) * 100;
    }
  }

  const reasoning = factors.join(". ") + ".";

  return {
    market,
    strategy: "statistical",
    confidence: Math.min(95, Math.max(5, confidence)),
    signal,
    favoredOutcome,
    reasoning,
    edge,
    tags,
  };
}
