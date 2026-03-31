/**
 * Core types for the AgentBook Pundit agent.
 */

// --- MCP / API Types ---

export interface McpResult {
  success: boolean;
  data?: any;
  error?: string;
}

export interface Market {
  id: string;
  pda: string;
  question: string;
  status: "active" | "closed" | "resolved";
  layer: "official" | "lab" | "private";
  category?: string;
  closingTime: string;
  createdAt: string;
  pool: MarketPool;
  outcomes: MarketOutcome[];
  volume?: number;
  creator?: string;
}

export interface MarketPool {
  total: number;
  outcomes: number[];
}

export interface MarketOutcome {
  index: number;
  label: string;
  probability: number;
  pool: number;
}

export interface RaceMarket extends Market {
  outcomes: MarketOutcome[];
}

export interface Quote {
  marketPda: string;
  side: string;
  amount: number;
  avgPrice: number;
  priceImpact: number;
  estimatedShares: number;
  impliedProbability: number;
}

// --- Analysis Types ---

export type AnalysisStrategy = "fundamental" | "statistical" | "contrarian";

export interface MarketAnalysis {
  market: Market;
  strategy: AnalysisStrategy;
  confidence: number; // 0-100
  signal: "bullish" | "bearish" | "neutral";
  favoredOutcome: string;
  reasoning: string;
  edge?: number; // estimated edge vs market odds
  tags: string[];
}

export interface AnalysisReport {
  timestamp: string;
  markets: Market[];
  analyses: MarketAnalysis[];
  topPick?: MarketAnalysis;
  summary: string;
}

// --- AgentBook Types ---

export interface AgentBookPost {
  id?: number;
  walletAddress: string;
  content: string;
  marketPda?: string | null;
  steams?: number;
  createdAt?: string;
  agent?: AgentProfile;
}

export interface AgentProfile {
  walletAddress: string;
  agentName: string;
  agentType: string;
  avatarUrl?: string | null;
}

export interface MarketComment {
  marketPda: string;
  content: string;
  walletAddress: string;
}

// --- Schedule Types ---

export type PostType = "roundup" | "odds-movement" | "closing-soon" | "deep-dive" | "contrarian";

export interface ScheduledPost {
  type: PostType;
  hour: number; // 0-23 UTC
  description: string;
}

export interface PostHistory {
  lastPostTime: string | null;
  lastCommentTime: string | null;
  postsToday: number;
  commentsToday: number;
  postedMarketPdas: string[];
}

// --- Config ---

export interface PunditConfig {
  walletAddress: string;
  solanaPrivateKey?: string;
  solanaRpcUrl?: string;
  postCooldownMs: number; // 30 min = 1800000
  commentCooldownMs: number; // 60 min = 3600000
  maxPostsPerDay: number;
  maxCommentsPerDay: number;
  minPostLength: number;
  maxPostLength: number;
  minCommentLength: number;
  maxCommentLength: number;
  dryRun: boolean;
  schedule: ScheduledPost[];
}

export const DEFAULT_CONFIG: PunditConfig = {
  walletAddress: "",
  postCooldownMs: 30 * 60 * 1000,
  commentCooldownMs: 60 * 60 * 1000,
  maxPostsPerDay: 8,
  maxCommentsPerDay: 12,
  minPostLength: 10,
  maxPostLength: 2000,
  minCommentLength: 10,
  maxCommentLength: 500,
  dryRun: false,
  schedule: [
    { type: "roundup", hour: 9, description: "Morning market roundup — top markets by volume" },
    { type: "odds-movement", hour: 14, description: "Midday odds movement alert — biggest shifts" },
    { type: "closing-soon", hour: 19, description: "Evening closing alert — markets closing within 24h" },
    { type: "deep-dive", hour: 22, description: "Late night deep dive — detailed analysis of one market" },
  ],
};
