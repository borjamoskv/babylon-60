#!/usr/bin/env bun
// CLI: Detect trending topics and display them
import { fetchCoinGeckoTrends } from "../sources/coingecko.ts";
import { fetchHackerNewsTrends } from "../sources/hackernews.ts";
import { fetchRSSFeeds } from "../sources/rss.ts";
import { mergeTopics } from "../market/dedup.ts";
import { generateMarketQuestion } from "../market/generator.ts";

async function main() {
  console.log("=== Trend Detection ===\n");

  const [cg, hn, rss] = await Promise.all([
    fetchCoinGeckoTrends().catch(() => []),
    fetchHackerNewsTrends().catch(() => []),
    fetchRSSFeeds().catch(() => []),
  ]);

  console.log(`CoinGecko: ${cg.length} trends`);
  for (const t of cg) console.log(`  [${t.score}] ${t.title}`);

  console.log(`\nHackerNews: ${hn.length} trends`);
  for (const t of hn) console.log(`  [${t.score}] ${t.title}`);

  console.log(`\nRSS Feeds: ${rss.length} trends`);
  for (const t of rss) console.log(`  [${t.score}] ${t.title} (${t.source})`);

  const all = mergeTopics([...cg, ...hn, ...rss]);
  console.log(`\n=== ${all.length} Unique Topics ===`);
  for (const t of all.sort((a, b) => b.score - a.score)) {
    const market = generateMarketQuestion(t);
    console.log(`\n[${t.score}] ${t.title}`);
    console.log(`  Source: ${t.source} | Category: ${t.category}`);
    if (market) {
      console.log(`  → Market: "${market.question}"`);
      console.log(`    Type ${market.timingType} | Close: ${market.closingTime.toISOString().split("T")[0]} | Source: ${market.dataSource}`);
    } else {
      console.log(`  → No market generated (topic doesn't match patterns)`);
    }
  }
}

main().catch(console.error);
