#!/usr/bin/env bun
// CLI: Validate a market question against Baozi rules
import { localValidate, remoteValidate } from "../market/validator.ts";
import type { MarketQuestion } from "../config.ts";

const question = process.argv[2];
if (!question) {
  console.log("Usage: bun run validate-market.ts <question>");
  console.log('Example: bun run validate-market.ts "Will BTC market cap exceed AAPL by March 1, 2026?"');
  process.exit(1);
}

const now = new Date();
const closingTime = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);

const eventTime = new Date(closingTime.getTime() + 24 * 60 * 60 * 1000);

const market: MarketQuestion = {
  question,
  description: "Auto-generated test market",
  marketType: "boolean",
  category: "crypto",
  closingTime,
  resolutionTime: new Date(eventTime.getTime() + 300 * 1000),
  dataSource: "Manual verification",
  dataSourceUrl: "",
  tags: ["test"],
  trendSource: { id: "test", title: question, source: "cli", category: "crypto", score: 50, detectedAt: now, metadata: {} },
  timingType: "A",
  eventTime,
};

console.log("=== Local Validation ===");
const local = localValidate(market);
console.log(`Approved: ${local.approved}`);
for (const v of local.violations) {
  console.log(`  [${v.severity}] ${v.rule}: ${v.message}`);
}

console.log("\n=== Remote Validation (Baozi API) ===");
const remote = await remoteValidate(market);
console.log(`Approved: ${remote.approved}`);
for (const v of remote.violations) {
  console.log(`  [${v.severity}] ${v.rule}: ${v.message}`);
}
