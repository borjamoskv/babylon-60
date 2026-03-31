// Baozi Parimutuel Rules v7.0 — shared constants

// Auto-reject any question containing these terms
export const BLOCKED_TERMS = [
  "price above", "price below", "trading volume", "market cap",
  "gains most", "total volume", "total burned", "average over",
  "this week", "this month", "floor price", "ath", "all-time high",
  "tvl", "total value locked",
];

export function containsBlockedTerm(text: string): boolean {
  const lower = text.toLowerCase();
  return BLOCKED_TERMS.some((term) => lower.includes(term));
}
