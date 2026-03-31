/**
 * Pundit Service
 *
 * Orchestrates the full flow: read markets → analyze → generate content → post.
 * Handles scheduling, cooldowns, and post selection.
 */
import { MarketReader } from "./market-reader.js";
import { AgentBookClient } from "./agentbook-client.js";
import { generateContent, generateMarketComment } from "./content-generator.js";
import { generateReport, analyzeMarketAll, getConsensus } from "../strategies/index.js";
import type { PunditConfig, PostType, AnalysisReport, Market } from "../types/index.js";
import { sleep } from "../utils/helpers.js";

export class Pundit {
  private reader: MarketReader;
  private client: AgentBookClient;
  private config: PunditConfig;
  private running = false;

  constructor(config: PunditConfig) {
    this.config = config;
    this.reader = new MarketReader();
    this.client = new AgentBookClient({
      walletAddress: config.walletAddress,
      privateKey: config.solanaPrivateKey,
      dryRun: config.dryRun,
    });
  }

  /**
   * Run a single analysis cycle: fetch markets, analyze, generate report.
   */
  async analyze(): Promise<AnalysisReport> {
    console.log("📡 Fetching active markets...");
    const markets = await this.reader.listMarkets({ status: "active", limit: 50 });
    console.log(`  Found ${markets.length} active markets`);

    // Also fetch race markets
    const raceMarkets = await this.reader.listRaceMarkets({ status: "active", limit: 20 });
    console.log(`  Found ${raceMarkets.length} race markets`);

    // Combine, dedup by PDA
    const seen = new Set<string>();
    const allMarkets: Market[] = [];
    for (const m of [...markets, ...raceMarkets]) {
      if (!seen.has(m.pda)) {
        seen.add(m.pda);
        allMarkets.push(m);
      }
    }

    console.log(`📊 Analyzing ${allMarkets.length} markets...`);
    const report = generateReport(allMarkets);
    console.log(`  Generated report with ${report.analyses.length} analyses`);
    if (report.topPick) {
      console.log(
        `  🎯 Top pick: "${report.topPick.market.question}" — ${report.topPick.signal} (${report.topPick.confidence}%)`
      );
    }

    return report;
  }

  /**
   * Post a specific type of take to AgentBook.
   */
  async post(type: PostType): Promise<{ success: boolean; error?: string }> {
    // Check if we can post
    const canPost = this.client.canPost(this.config.maxPostsPerDay);
    if (!canPost.allowed) {
      console.log(`⏳ Cannot post: ${canPost.reason}`);
      return { success: false, error: canPost.reason };
    }

    // Run analysis
    const report = await this.analyze();

    if (report.analyses.length === 0) {
      return { success: false, error: "No markets to analyze" };
    }

    // Generate content
    const { content, marketPda } = generateContent(type, report);
    console.log(`\n📝 Generated ${type} post (${content.length} chars):`);
    console.log("---");
    console.log(content);
    console.log("---\n");

    // Post it
    const result = await this.client.postTake(content, marketPda);
    if (result.success) {
      console.log("✅ Posted to AgentBook!");
    } else {
      console.log(`❌ Failed to post: ${result.error}`);
    }

    return result;
  }

  /**
   * Comment on a specific market with analysis.
   */
  async comment(marketPda: string): Promise<{ success: boolean; error?: string }> {
    const canComment = this.client.canComment(this.config.maxCommentsPerDay);
    if (!canComment.allowed) {
      console.log(`⏳ Cannot comment: ${canComment.reason}`);
      return { success: false, error: canComment.reason };
    }

    // Get market details and analyze
    const market = await this.reader.getMarketDetails(marketPda);
    if (!market) {
      return { success: false, error: `Market ${marketPda} not found` };
    }

    const analyses = analyzeMarketAll(market);
    const consensus = getConsensus(analyses);
    if (!consensus) {
      return { success: false, error: "Failed to analyze market" };
    }

    const commentText = generateMarketComment(consensus);
    console.log(`💬 Generated comment (${commentText.length} chars): ${commentText}`);

    const result = await this.client.postComment(marketPda, commentText);
    if (result.success) {
      console.log("✅ Comment posted!");
    } else {
      console.log(`❌ Failed to comment: ${result.error}`);
    }

    return result;
  }

  /**
   * Comment on top markets (by volume or interest).
   */
  async commentOnTopMarkets(count: number = 3): Promise<void> {
    const topMarkets = await this.reader.getTopByVolume(count);
    for (const market of topMarkets) {
      const canComment = this.client.canComment(this.config.maxCommentsPerDay);
      if (!canComment.allowed) {
        console.log(`⏳ Stopping comments: ${canComment.reason}`);
        break;
      }

      await this.comment(market.pda);
      // Respect cooldown
      if (topMarkets.indexOf(market) < topMarkets.length - 1) {
        console.log("⏳ Waiting for comment cooldown...");
        await sleep(this.config.commentCooldownMs + 60000); // +1min buffer
      }
    }
  }

  /**
   * Run the scheduled posting loop.
   */
  async run(): Promise<void> {
    this.running = true;
    console.log("🚀 AgentBook Pundit starting...");
    console.log(`   Wallet: ${this.config.walletAddress}`);
    console.log(`   Dry run: ${this.config.dryRun}`);
    console.log(`   Schedule: ${this.config.schedule.length} posts/day\n`);

    while (this.running) {
      const now = new Date();
      const currentHour = now.getUTCHours();

      // Check if any scheduled post should fire
      for (const scheduled of this.config.schedule) {
        if (scheduled.hour === currentHour) {
          console.log(`\n🕐 Scheduled: ${scheduled.description}`);
          await this.post(scheduled.type);

          // Also comment on a market after certain post types
          if (scheduled.type === "deep-dive" || scheduled.type === "contrarian") {
            await sleep(5000);
            await this.commentOnTopMarkets(1);
          }
        }
      }

      // Reset daily counters at midnight
      if (currentHour === 0) {
        this.client.resetDailyCounters();
      }

      // Sleep until next hour
      const nextHour = new Date(now);
      nextHour.setUTCHours(currentHour + 1, 0, 0, 0);
      const sleepMs = nextHour.getTime() - Date.now();
      console.log(`💤 Sleeping ${Math.round(sleepMs / 60000)} minutes until next check...`);
      await sleep(sleepMs);
    }
  }

  /**
   * Stop the running loop.
   */
  stop(): void {
    this.running = false;
    console.log("🛑 Pundit stopping...");
  }

  /**
   * Get the AgentBook client for direct access.
   */
  getClient(): AgentBookClient {
    return this.client;
  }

  /**
   * Get the market reader for direct access.
   */
  getReader(): MarketReader {
    return this.reader;
  }
}
