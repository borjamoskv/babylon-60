/**
 * Fundamental Analysis Strategy
 *
 * Evaluates market odds based on the underlying question,
 * pool size, market structure, and real-world context.
 */
import type { Market, MarketAnalysis } from "../types/index.js";
import { hoursUntil, formatSol, categorizeQuestion } from "../utils/helpers.js";

export function analyzeFundamental(market: Market): MarketAnalysis {
  const tags: string[] = ["fundamental"];
  const factors: string[] = [];
  let confidence = 50;
  let signal: "bullish" | "bearish" | "neutral" = "neutral";
  let favoredOutcome = market.outcomes[0]?.label || "Yes";
  let edge = 0;

  const hoursLeft = hoursUntil(market.closingTime);
  const totalPool = market.pool.total;
  const category = categorizeQuestion(market.question);
  tags.push(category);

  // 1. Pool size analysis
  if (totalPool < 0.1) {
    factors.push(`Tiny pool (${formatSol(totalPool)}) — low confidence, easily manipulated`);
    confidence -= 15;
    tags.push("low-liquidity");
  } else if (totalPool > 5) {
    factors.push(`Strong pool (${formatSol(totalPool)}) — higher signal quality`);
    confidence += 10;
    tags.push("high-liquidity");
  }

  // 2. Time analysis
  if (hoursLeft <= 0) {
    factors.push("Market expired — skip");
    confidence = 0;
  } else if (hoursLeft < 6) {
    factors.push(`Closing very soon (${hoursLeft.toFixed(1)}h) — odds likely final`);
    tags.push("closing-soon");
    confidence += 5; // Late-stage odds more reliable
  } else if (hoursLeft < 24) {
    factors.push(`Closing within 24h (${hoursLeft.toFixed(1)}h)`);
    tags.push("closing-soon");
  } else if (hoursLeft > 168) {
    factors.push(`Long-dated (${Math.floor(hoursLeft / 24)} days) — odds may drift significantly`);
    tags.push("long-dated");
    confidence -= 5;
  }

  // 3. Odds skew analysis
  const primaryProb = market.outcomes[0]?.probability || 0.5;
  if (primaryProb > 0.9) {
    factors.push(`Heavy favorite at ${(primaryProb * 100).toFixed(0)}% — near-certain per market`);
    signal = "bullish";
    favoredOutcome = market.outcomes[0].label;
    confidence += 10;

    // Check if extreme odds make sense for the question type
    if (totalPool < 0.5) {
      factors.push("But low pool means this extreme pricing might be noise");
      confidence -= 10;
    }
  } else if (primaryProb < 0.1) {
    factors.push(`Heavy underdog at ${(primaryProb * 100).toFixed(0)}%`);
    signal = "bearish";
    favoredOutcome = market.outcomes[1]?.label || "No";
    confidence += 10;
  } else if (Math.abs(primaryProb - 0.5) < 0.05) {
    factors.push(`Near 50/50 (${(primaryProb * 100).toFixed(0)}%) — market is undecided`);
    signal = "neutral";
    tags.push("coin-flip");
  } else {
    // Moderate lean
    if (primaryProb > 0.5) {
      signal = "bullish";
      favoredOutcome = market.outcomes[0].label;
    } else {
      signal = "bearish";
      favoredOutcome = market.outcomes[1]?.label || "No";
    }
    factors.push(`Moderate lean: ${favoredOutcome} at ${(Math.max(primaryProb, 1 - primaryProb) * 100).toFixed(0)}%`);
  }

  // 4. Outcome count (race markets)
  if (market.outcomes.length > 2) {
    tags.push("race-market");
    factors.push(`Race market with ${market.outcomes.length} outcomes`);

    // Find the leader
    const sorted = [...market.outcomes].sort((a, b) => b.probability - a.probability);
    favoredOutcome = sorted[0].label;
    const leaderProb = sorted[0].probability;
    const runnerProb = sorted[1]?.probability || 0;

    if (leaderProb - runnerProb > 0.2) {
      factors.push(`Clear leader: ${favoredOutcome} at ${(leaderProb * 100).toFixed(0)}% (next: ${(runnerProb * 100).toFixed(0)}%)`);
      confidence += 5;
    } else {
      factors.push(`Tight race between top ${Math.min(3, sorted.length)} outcomes`);
    }
  }

  // 5. Category-specific adjustments
  if (category === "crypto") {
    factors.push("Crypto market — high volatility, binary outcomes often coin-flips");
    if (Math.abs(primaryProb - 0.5) < 0.15) {
      confidence -= 5; // Crypto near 50/50 is genuinely uncertain
    }
  } else if (category === "sports") {
    factors.push("Sports market — historical data usually well-priced");
    confidence += 5;
  }

  // Calculate edge estimate
  const marketProb = signal === "bullish" ? primaryProb : 1 - primaryProb;
  edge = Math.max(0, (confidence / 100) - marketProb) * 100;

  const reasoning = factors.join(". ") + ".";

  return {
    market,
    strategy: "fundamental",
    confidence: Math.min(95, Math.max(5, confidence)),
    signal,
    favoredOutcome,
    reasoning,
    edge,
    tags,
  };
}
