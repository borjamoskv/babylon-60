/**
 * AgentBook Pundit — AI Market Analyst
 *
 * Reads active Baozi markets, analyzes odds using multiple strategies,
 * and posts public takes on AgentBook (baozi.bet/agentbook).
 */
export { Pundit } from "./services/pundit.js";
export { MarketReader } from "./services/market-reader.js";
export { AgentBookClient } from "./services/agentbook-client.js";
export { analyzeMarket, analyzeMarketAll, getConsensus, generateReport } from "./strategies/index.js";
export { analyzeFundamental } from "./strategies/fundamental.js";
export { analyzeStatistical } from "./strategies/statistical.js";
export { analyzeContrarian } from "./strategies/contrarian.js";
export {
  generateRoundup,
  generateOddsMovement,
  generateClosingSoon,
  generateDeepDive,
  generateContrarianTake,
  generateMarketComment,
  generateContent,
} from "./services/content-generator.js";
export * from "./types/index.js";
