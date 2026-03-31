/**
 * Test fixtures — reusable market and analysis data for tests.
 */
import type { Market, MarketAnalysis } from "../types/index.js";

export function makeMarket(overrides: Partial<Market> = {}): Market {
  const defaults: Market = {
    id: "test-market-1",
    pda: "abc123def456",
    question: "Will BTC hit $100k by March 2026?",
    status: "active",
    layer: "official",
    category: "crypto",
    closingTime: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days
    createdAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    pool: { total: 5.0, outcomes: [3.0, 2.0] },
    outcomes: [
      { index: 0, label: "Yes", probability: 0.6, pool: 3.0 },
      { index: 1, label: "No", probability: 0.4, pool: 2.0 },
    ],
    volume: 5.0,
  };
  return { ...defaults, ...overrides };
}

export function makeHeavyFavorite(): Market {
  return makeMarket({
    id: "heavy-fav",
    pda: "heavy-fav-pda",
    question: "Will Baozi tweet a pizza emoji by March 1st?",
    pool: { total: 0.05, outcomes: [0.05, 0.0] },
    outcomes: [
      { index: 0, label: "Yes", probability: 1.0, pool: 0.05 },
      { index: 1, label: "No", probability: 0.0, pool: 0.0 },
    ],
    volume: 0.05,
  });
}

export function makeCoinFlip(): Market {
  return makeMarket({
    id: "coin-flip",
    pda: "coin-flip-pda",
    question: "Will ETH be above $2800 on Feb 25?",
    pool: { total: 2.0, outcomes: [1.0, 1.0] },
    outcomes: [
      { index: 0, label: "Yes", probability: 0.5, pool: 1.0 },
      { index: 1, label: "No", probability: 0.5, pool: 1.0 },
    ],
    volume: 2.0,
  });
}

export function makeClosingSoon(): Market {
  return makeMarket({
    id: "closing-soon",
    pda: "closing-soon-pda",
    question: "Will it rain in NYC today?",
    category: "weather",
    closingTime: new Date(Date.now() + 3 * 60 * 60 * 1000).toISOString(), // 3 hours
    pool: { total: 1.5, outcomes: [0.9, 0.6] },
    outcomes: [
      { index: 0, label: "Yes", probability: 0.6, pool: 0.9 },
      { index: 1, label: "No", probability: 0.4, pool: 0.6 },
    ],
  });
}

export function makeLongDated(): Market {
  return makeMarket({
    id: "long-dated",
    pda: "long-dated-pda",
    question: "Will Trump win the 2028 election?",
    category: "politics",
    closingTime: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
    pool: { total: 10.0, outcomes: [6.0, 4.0] },
    outcomes: [
      { index: 0, label: "Yes", probability: 0.6, pool: 6.0 },
      { index: 1, label: "No", probability: 0.4, pool: 4.0 },
    ],
  });
}

export function makeRaceMarket(): Market {
  return makeMarket({
    id: "race-market",
    pda: "race-market-pda",
    question: "Who will win Best Picture at BAFTA?",
    category: "entertainment",
    pool: { total: 3.0, outcomes: [1.2, 0.9, 0.6, 0.3] },
    outcomes: [
      { index: 0, label: "The Brutalist", probability: 0.4, pool: 1.2 },
      { index: 1, label: "Conclave", probability: 0.3, pool: 0.9 },
      { index: 2, label: "Anora", probability: 0.2, pool: 0.6 },
      { index: 3, label: "Emilia Pérez", probability: 0.1, pool: 0.3 },
    ],
  });
}

export function makeLowLiquidity(): Market {
  return makeMarket({
    id: "low-liq",
    pda: "low-liq-pda",
    question: "Will SOL hit $300 this month?",
    pool: { total: 0.02, outcomes: [0.01, 0.01] },
    outcomes: [
      { index: 0, label: "Yes", probability: 0.5, pool: 0.01 },
      { index: 1, label: "No", probability: 0.5, pool: 0.01 },
    ],
    volume: 0.02,
  });
}

export function makeHighLiquidity(): Market {
  return makeMarket({
    id: "high-liq",
    pda: "high-liq-pda",
    question: "Will Netflix top 300M subscribers by Q2?",
    category: "entertainment",
    pool: { total: 50.0, outcomes: [30.0, 20.0] },
    outcomes: [
      { index: 0, label: "Yes", probability: 0.6, pool: 30.0 },
      { index: 1, label: "No", probability: 0.4, pool: 20.0 },
    ],
    volume: 50.0,
  });
}

export function makeExpired(): Market {
  return makeMarket({
    id: "expired",
    pda: "expired-pda",
    question: "Has this already happened?",
    closingTime: new Date(Date.now() - 60 * 60 * 1000).toISOString(), // 1 hour ago
  });
}

export function makeExtremeLongshot(): Market {
  return makeMarket({
    id: "longshot",
    pda: "longshot-pda",
    question: "Will aliens land on Earth this month?",
    pool: { total: 1.0, outcomes: [0.05, 0.95] },
    outcomes: [
      { index: 0, label: "Yes", probability: 0.05, pool: 0.05 },
      { index: 1, label: "No", probability: 0.95, pool: 0.95 },
    ],
  });
}

export function makeSportsMarket(): Market {
  return makeMarket({
    id: "sports",
    pda: "sports-pda",
    question: "Will the Lakers win the NBA Championship?",
    category: "sports",
    pool: { total: 8.0, outcomes: [3.0, 5.0] },
    outcomes: [
      { index: 0, label: "Yes", probability: 0.375, pool: 3.0 },
      { index: 1, label: "No", probability: 0.625, pool: 5.0 },
    ],
  });
}
