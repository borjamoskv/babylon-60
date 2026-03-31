/**
 * Contrarian Analysis Strategy
 *
 * Looks for markets where the crowd might be wrong.
 * Identifies overreactions, herding behavior, and
 * opportunities where the underdog has hidden value.
 */
import type { Market, MarketAnalysis } from "../types/index.js";
import { hoursUntil, formatSol, formatPercent } from "../utils/helpers.js";

export function analyzeContrarian(market: Market): MarketAnalysis {
  const tags: string[] = ["contrarian"];
  const factors: string[] = [];
  let confidence = 40; // Start lower — contrarian picks need stronger evidence
  let signal: "bullish" | "bearish" | "neutral" = "neutral";
  let favoredOutcome = market.outcomes[0]?.label || "Yes";
  let edge = 0;

  const totalPool = market.pool.total;
  const hoursLeft = hoursUntil(market.closingTime);

  // 1. Extreme odds = potential contrarian play
  const primaryProb = market.outcomes[0]?.probability || 0.5;

  if (primaryProb > 0.9) {
    // Market says 90%+ Yes — is No underpriced?
    factors.push(
      `Market at ${formatPercent(primaryProb)} Yes — extreme certainty. Is this warranted?`
    );

    if (totalPool < 1) {
      factors.push(
        `Low pool ${formatSol(totalPool)} — extreme odds likely from few participants, not consensus`
      );
      signal = "bearish"; // Lean contrarian on No
      favoredOutcome = market.outcomes[1]?.label || "No";
      confidence += 15;
      edge = (0.2 - (1 - primaryProb)) * 100; // Assume true prob is at least 20% No
      tags.push("crowd-herding");
    } else {
      factors.push(
        `High pool ${formatSol(totalPool)} — consensus might be correct. Contrarian play risky.`
      );
      confidence -= 10;
    }
  } else if (primaryProb < 0.1) {
    // Market says 90%+ No — is Yes underpriced?
    factors.push(
      `Market at ${formatPercent(primaryProb)} Yes — consensus strongly against`
    );

    if (totalPool < 1) {
      signal = "bullish";
      favoredOutcome = market.outcomes[0]?.label || "Yes";
      confidence += 15;
      edge = (0.2 - primaryProb) * 100;
      factors.push("Low liquidity extreme odds — contrarian value possible");
      tags.push("crowd-herding");
    }
  }

  // 2. 50/50 markets with time pressure
  if (Math.abs(primaryProb - 0.5) < 0.08 && hoursLeft < 48) {
    factors.push(
      `Near 50/50 with only ${hoursLeft.toFixed(0)}h left — market undecided late in the game`
    );
    factors.push("Last-minute info could swing this hard. Watch for movement.");
    tags.push("undecided-late");
    confidence += 5;
  }

  // 3. Pool asymmetry detection
  if (market.outcomes.length === 2 && totalPool > 0) {
    const ratio = market.outcomes[0].pool / (market.outcomes[1].pool || 0.0001);

    if (ratio > 10) {
      factors.push(
        `Pool ratio ${ratio.toFixed(0)}:1 — massive crowd on ${market.outcomes[0].label}. Contrarian ${market.outcomes[1].label} has high payoff.`
      );
      signal = "bearish";
      favoredOutcome = market.outcomes[1].label;
      edge = Math.min(30, ratio * 2);
      tags.push("asymmetric-payoff");
    } else if (ratio < 0.1) {
      factors.push(
        `Pool ratio 1:${(1 / ratio).toFixed(0)} — massive crowd on ${market.outcomes[1].label}. Contrarian ${market.outcomes[0].label} has high payoff.`
      );
      signal = "bullish";
      favoredOutcome = market.outcomes[0].label;
      edge = Math.min(30, (1 / ratio) * 2);
      tags.push("asymmetric-payoff");
    }
  }

  // 4. Race market: find overlooked outcomes
  if (market.outcomes.length > 2) {
    const sorted = [...market.outcomes].sort((a, b) => a.probability - b.probability);
    const lowestProb = sorted[0];
    const highestProb = sorted[sorted.length - 1];

    if (lowestProb.probability < 0.1 && market.outcomes.length >= 3) {
      factors.push(
        `${lowestProb.label} at ${formatPercent(lowestProb.probability)} — overlooked outcome with huge potential payoff`
      );

      // Check if it's a reasonable contrarian pick
      if (totalPool < 2) {
        factors.push("Low total pool makes this a speculative contrarian play");
        signal = "neutral"; // Don't commit signal on race market longshots
        favoredOutcome = lowestProb.label;
        confidence += 5;
        tags.push("dark-horse");
      }
    }

    // Check for false favorites in race markets
    if (highestProb.probability > 0.5 && market.outcomes.length > 3) {
      factors.push(
        `${highestProb.label} at ${formatPercent(highestProb.probability)} in ${market.outcomes.length}-way race — possibly overrated`
      );
      tags.push("questionable-favorite");
    }
  }

  // 5. Time-based contrarian signals
  if (hoursLeft > 168) {
    factors.push("Long-dated market — early odds rarely hold. Current pricing is noisy.");
    confidence -= 5;
    tags.push("early-stage");
  } else if (hoursLeft < 2 && totalPool > 1) {
    factors.push("About to close — contrarian play unlikely to flip. Go with the crowd.");
    confidence -= 20;
    signal = "neutral";
  }

  // 6. "New market" contrarian advantage
  if (totalPool < 0.2 && hoursLeft > 48 && !tags.includes("crowd-herding") && !tags.includes("asymmetric-payoff")) {
    factors.push(
      "Fresh market with minimal liquidity — first mover can set the price. Wait for more participants."
    );
    tags.push("new-market");
    confidence = 20;
    signal = "neutral";
  }

  const reasoning = factors.length > 0
    ? factors.join(". ") + "."
    : "No strong contrarian signals detected. Market appears efficiently priced.";

  return {
    market,
    strategy: "contrarian",
    confidence: Math.min(85, Math.max(5, confidence)),
    signal,
    favoredOutcome,
    reasoning,
    edge: Math.max(0, edge),
    tags,
  };
}
