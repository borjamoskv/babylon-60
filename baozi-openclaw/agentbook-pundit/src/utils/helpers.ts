/**
 * Utility helpers for the AgentBook Pundit agent.
 */

/**
 * Hours until a given ISO timestamp.
 */
export function hoursUntil(isoDate: string): number {
  const target = new Date(isoDate).getTime();
  const now = Date.now();
  return (target - now) / (1000 * 60 * 60);
}

/**
 * Format SOL amount for display.
 */
export function formatSol(amount: number): string {
  if (amount >= 1000) return `${(amount / 1000).toFixed(1)}K SOL`;
  if (amount >= 1) return `${amount.toFixed(2)} SOL`;
  if (amount >= 0.01) return `${amount.toFixed(3)} SOL`;
  return `${amount.toFixed(4)} SOL`;
}

/**
 * Format a probability/percentage.
 */
export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

/**
 * Categorize a market question into a topic.
 */
export function categorizeQuestion(question: string): string {
  const q = question.toLowerCase();

  if (/\b(btc|bitcoin|eth|ethereum|sol|solana|crypto|token|defi|nft|chain)\b/.test(q)) {
    return "crypto";
  }
  if (/\b(trump|biden|election|congress|senate|president|governor|vote|political|policy)\b/.test(q)) {
    return "politics";
  }
  if (/\b(movie|film|oscar|grammy|emmy|album|song|netflix|spotify|billboard|bafta|award)\b/.test(q)) {
    return "entertainment";
  }
  if (/\b(team|nba|nfl|mlb|nhl|soccer|football|match|game|win|championship|league|tournament|score)\b/.test(q)) {
    return "sports";
  }
  if (/\b(weather|temperature|rain|snow|storm|hurricane)\b/.test(q)) {
    return "weather";
  }
  if (/\b(ai|gpt|llm|model|openai|anthropic|google|apple|meta|microsoft|tech)\b/.test(q)) {
    return "tech";
  }
  return "general";
}

/**
 * Truncate text to a maximum length, adding ellipsis if needed.
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + "...";
}

/**
 * Format a date for display.
 */
export function formatDate(isoDate: string): string {
  const d = new Date(isoDate);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

/**
 * Sleep for a given number of milliseconds.
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Generate a market URL.
 */
export function marketUrl(pda: string): string {
  return `baozi.bet/market/${pda}`;
}

/**
 * Pick a random element from an array.
 */
export function pickRandom<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

/**
 * Generate a unique-ish ID.
 */
export function genId(): string {
  return Date.now().toString(36) + Math.random().toString(36).substring(2, 6);
}
