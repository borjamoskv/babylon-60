/**
 * Content Generator
 *
 * Transforms market analyses into formatted posts for AgentBook
 * and comments for individual markets. Each post type has its
 * own template and style.
 */
import type { Market, MarketAnalysis, AnalysisReport, PostType } from "../types/index.js";
import { formatSol, formatPercent, hoursUntil, truncate, marketUrl, pickRandom } from "../utils/helpers.js";

const EMOJI_MAP: Record<string, string> = {
  crypto: "₿",
  sports: "⚽",
  politics: "🏛️",
  entertainment: "🎬",
  weather: "🌤️",
  tech: "🤖",
  general: "📊",
  bullish: "🟢",
  bearish: "🔴",
  neutral: "⚖️",
};

/**
 * Generate a morning roundup post — top markets by volume.
 */
export function generateRoundup(report: AnalysisReport): string {
  const top = report.analyses.slice(0, 5);
  if (top.length === 0) return "📊 Market Roundup: No active markets to report. Stay tuned!";

  const lines: string[] = ["📊 Baozi Market Roundup\n"];

  for (const analysis of top) {
    const m = analysis.market;
    const emoji = EMOJI_MAP[analysis.tags.find((t) => EMOJI_MAP[t]) || "general"];
    const prob = m.outcomes[0]?.probability || 0.5;
    const hrs = hoursUntil(m.closingTime);

    lines.push(
      `${emoji} "${truncate(m.question, 60)}" — ${formatPercent(prob)} Yes | Pool: ${formatSol(m.pool.total)} | ${hrs > 24 ? `${Math.floor(hrs / 24)}d` : `${Math.floor(hrs)}h`} left`
    );
  }

  if (report.topPick) {
    const tp = report.topPick;
    lines.push(
      `\n🎯 Top Pick: "${truncate(tp.market.question, 50)}" — ${tp.signal} on ${tp.favoredOutcome} (${tp.confidence}% confidence)`
    );
  }

  lines.push(`\n${top.length} markets analyzed at ${new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}`);

  return truncate(lines.join("\n"), 2000);
}

/**
 * Generate an odds movement alert — biggest shifts.
 */
export function generateOddsMovement(
  analyses: MarketAnalysis[],
  previousAnalyses?: MarketAnalysis[]
): string {
  // Without historical data, focus on markets with extreme or interesting odds
  const interesting = analyses.filter(
    (a) =>
      a.tags.includes("anomaly") ||
      a.tags.includes("value-bet") ||
      a.tags.includes("crowd-herding") ||
      a.confidence > 70
  );

  if (interesting.length === 0) {
    // Fallback: pick the most confident analyses
    const sorted = [...analyses].sort((a, b) => b.confidence - a.confidence);
    const top3 = sorted.slice(0, 3);

    if (top3.length === 0) return "📈 Odds Alert: Markets quiet today. No significant movements detected.";

    const lines: string[] = ["📈 Midday Odds Check\n"];
    for (const a of top3) {
      const signalEmoji = EMOJI_MAP[a.signal];
      lines.push(
        `${signalEmoji} "${truncate(a.market.question, 55)}" — ${a.favoredOutcome} favored at ${a.confidence}% confidence`
      );
    }
    return truncate(lines.join("\n"), 2000);
  }

  const lines: string[] = ["📈 Odds Movement Alert\n"];
  for (const a of interesting.slice(0, 4)) {
    const signalEmoji = EMOJI_MAP[a.signal];
    const tags = a.tags.filter((t) => !["fundamental", "statistical", "contrarian"].includes(t));
    lines.push(
      `${signalEmoji} "${truncate(a.market.question, 55)}" — ${a.reasoning.split(".")[0]}. [${tags.join(", ")}]`
    );
  }

  return truncate(lines.join("\n"), 2000);
}

/**
 * Generate a closing-soon alert.
 */
export function generateClosingSoon(markets: Market[]): string {
  const closing = markets
    .filter((m) => hoursUntil(m.closingTime) > 0 && hoursUntil(m.closingTime) < 24)
    .sort((a, b) => hoursUntil(a.closingTime) - hoursUntil(b.closingTime));

  if (closing.length === 0) {
    return "⏰ No markets closing in the next 24 hours. All quiet on the prediction front.";
  }

  const lines: string[] = ["⏰ Markets Closing Soon!\n"];

  for (const m of closing.slice(0, 5)) {
    const hrs = hoursUntil(m.closingTime);
    const prob = m.outcomes[0]?.probability || 0.5;
    const urgency = hrs < 2 ? "🔥" : hrs < 6 ? "⚡" : "🕐";

    lines.push(
      `${urgency} "${truncate(m.question, 55)}" — ${formatPercent(prob)} Yes | Pool: ${formatSol(m.pool.total)} | ${hrs < 1 ? `${Math.floor(hrs * 60)}min` : `${hrs.toFixed(1)}h`} left`
    );
  }

  lines.push(`\nLast chance to take a position! ${marketUrl(closing[0].pda)}`);

  return truncate(lines.join("\n"), 2000);
}

/**
 * Generate a deep-dive analysis post for a single market.
 */
export function generateDeepDive(analyses: MarketAnalysis[]): string {
  if (analyses.length === 0) return "🔍 No market selected for deep dive today.";

  // Pick the most interesting market
  const sorted = [...analyses].sort((a, b) => {
    const scoreA = a.confidence + (a.edge || 0) * 2;
    const scoreB = b.confidence + (b.edge || 0) * 2;
    return scoreB - scoreA;
  });

  const pick = sorted[0];
  const m = pick.market;
  const hrs = hoursUntil(m.closingTime);

  const lines: string[] = [
    `🔍 Deep Dive: "${truncate(m.question, 70)}"\n`,
  ];

  // Market stats
  lines.push(`📊 Pool: ${formatSol(m.pool.total)} | Closes: ${hrs > 24 ? `${Math.floor(hrs / 24)} days` : `${hrs.toFixed(1)}h`}`);

  // Outcomes
  lines.push("\nOdds breakdown:");
  for (const o of m.outcomes) {
    const bar = "█".repeat(Math.round(o.probability * 20)) + "░".repeat(20 - Math.round(o.probability * 20));
    lines.push(`  ${o.label}: ${formatPercent(o.probability)} ${bar} (${formatSol(o.pool)})`);
  }

  // Analysis
  lines.push(`\n📝 Analysis (${pick.confidence}% confidence):`);
  lines.push(pick.reasoning);

  // Verdict
  const signalEmoji = EMOJI_MAP[pick.signal];
  lines.push(`\n${signalEmoji} Verdict: ${pick.signal.toUpperCase()} on ${pick.favoredOutcome}`);
  if (pick.edge && pick.edge > 5) {
    lines.push(`Estimated edge: ${pick.edge.toFixed(1)}%`);
  }

  lines.push(`\n${marketUrl(m.pda)}`);

  return truncate(lines.join("\n"), 2000);
}

/**
 * Generate a contrarian take post.
 */
export function generateContrarianTake(analyses: MarketAnalysis[]): string {
  const contrarian = analyses.filter(
    (a) =>
      a.tags.includes("crowd-herding") ||
      a.tags.includes("asymmetric-payoff") ||
      a.tags.includes("dark-horse") ||
      a.tags.includes("questionable-favorite")
  );

  if (contrarian.length === 0) {
    // Fallback: generate a general contrarian observation
    const extreme = analyses.filter(
      (a) => a.market.outcomes[0]?.probability > 0.85 || a.market.outcomes[0]?.probability < 0.15
    );
    if (extreme.length === 0) {
      return "🤔 No strong contrarian signals today. Markets seem fairly priced. Sometimes the crowd is right!";
    }

    const pick = extreme[0];
    return truncate(
      `🤔 Contrarian Watch: "${truncate(pick.market.question, 50)}" at ${formatPercent(pick.market.outcomes[0].probability)} — extreme odds in a ${formatSol(pick.market.pool.total)} pool. The crowd is very confident, but is it justified? Worth watching for movement.\n\n${marketUrl(pick.market.pda)}`,
      2000
    );
  }

  const pick = contrarian[0];
  const m = pick.market;

  const openers = [
    "🤔 Going against the grain here...",
    "🤔 The crowd might be wrong on this one:",
    "🤔 Contrarian alert — overlooked angle:",
    "🤔 Playing devil's advocate:",
  ];

  return truncate(
    `${pickRandom(openers)}\n\n"${truncate(m.question, 60)}" — ${pick.reasoning}\n\n${EMOJI_MAP[pick.signal]} Lean: ${pick.favoredOutcome} (${pick.confidence}% confidence, ${(pick.edge || 0).toFixed(0)}% estimated edge)\n\n${marketUrl(m.pda)}`,
    2000
  );
}

/**
 * Generate a market comment (shorter, 10-500 chars).
 */
export function generateMarketComment(analysis: MarketAnalysis): string {
  const m = analysis.market;
  const signalEmoji = EMOJI_MAP[analysis.signal];

  const templates = [
    `${signalEmoji} ${analysis.favoredOutcome} at ${analysis.confidence}% confidence. ${analysis.reasoning.split(".")[0]}.`,
    `Pool: ${formatSol(m.pool.total)}. ${analysis.signal === "bullish" ? "Leaning Yes" : analysis.signal === "bearish" ? "Leaning No" : "On the fence"}. ${analysis.reasoning.split(".")[0]}.`,
    `${signalEmoji} ${analysis.reasoning.split(".").slice(0, 2).join(". ")}. Edge: ${(analysis.edge || 0).toFixed(0)}%.`,
  ];

  const comment = pickRandom(templates);
  return truncate(comment, 500);
}

/**
 * Generate content for a given post type.
 */
export function generateContent(
  type: PostType,
  report: AnalysisReport
): { content: string; marketPda?: string } {
  switch (type) {
    case "roundup":
      return { content: generateRoundup(report) };

    case "odds-movement":
      return { content: generateOddsMovement(report.analyses) };

    case "closing-soon":
      return { content: generateClosingSoon(report.markets) };

    case "deep-dive": {
      const content = generateDeepDive(report.analyses);
      const pda = report.topPick?.market.pda;
      return { content, marketPda: pda };
    }

    case "contrarian": {
      const content = generateContrarianTake(report.analyses);
      const contrarianPick = report.analyses.find((a) =>
        a.tags.includes("crowd-herding") || a.tags.includes("asymmetric-payoff")
      );
      return { content, marketPda: contrarianPick?.market.pda };
    }
  }
}
