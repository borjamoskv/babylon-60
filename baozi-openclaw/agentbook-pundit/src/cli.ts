#!/usr/bin/env node
/**
 * AgentBook Pundit CLI
 *
 * Commands:
 *   run       — Start the scheduled posting loop
 *   post      — Post a single take (roundup|odds-movement|closing-soon|deep-dive|contrarian)
 *   comment   — Comment on a specific market
 *   analyze   — Run analysis and print report (no posting)
 *   status    — Check AgentBook for existing posts
 */
import { Command } from "commander";
import { Pundit } from "./services/pundit.js";
import { DEFAULT_CONFIG } from "./types/index.js";
import type { PunditConfig, PostType } from "./types/index.js";

function getConfig(opts: any): PunditConfig {
  return {
    ...DEFAULT_CONFIG,
    walletAddress: opts.wallet || process.env.WALLET_ADDRESS || "",
    solanaPrivateKey: process.env.SOLANA_PRIVATE_KEY,
    solanaRpcUrl: process.env.SOLANA_RPC_URL,
    dryRun: opts.dryRun || false,
  };
}

const program = new Command();

program
  .name("agentbook-pundit")
  .description("AI Market Analyst — analyze Baozi markets and post takes on AgentBook")
  .version("1.0.0")
  .option("-w, --wallet <address>", "Wallet address for AgentBook")
  .option("--dry-run", "Don't actually post (preview mode)");

program
  .command("run")
  .description("Start the scheduled posting loop (runs continuously)")
  .action(async () => {
    const config = getConfig(program.opts());
    if (!config.walletAddress) {
      console.error("❌ Wallet address required. Use --wallet or set WALLET_ADDRESS env var.");
      process.exit(1);
    }
    const pundit = new Pundit(config);

    // Handle graceful shutdown
    process.on("SIGINT", () => {
      pundit.stop();
      process.exit(0);
    });

    await pundit.run();
  });

program
  .command("post [type]")
  .description("Post a single take (roundup|odds-movement|closing-soon|deep-dive|contrarian)")
  .action(async (type: string = "roundup") => {
    const validTypes: PostType[] = ["roundup", "odds-movement", "closing-soon", "deep-dive", "contrarian"];
    if (!validTypes.includes(type as PostType)) {
      console.error(`❌ Invalid post type: ${type}. Valid: ${validTypes.join(", ")}`);
      process.exit(1);
    }
    const config = getConfig(program.opts());
    if (!config.walletAddress) {
      console.error("❌ Wallet address required. Use --wallet or set WALLET_ADDRESS env var.");
      process.exit(1);
    }
    const pundit = new Pundit(config);
    await pundit.post(type as PostType);
  });

program
  .command("comment <marketPda>")
  .description("Comment on a specific market with analysis")
  .action(async (marketPda: string) => {
    const config = getConfig(program.opts());
    if (!config.walletAddress) {
      console.error("❌ Wallet address required. Use --wallet or set WALLET_ADDRESS env var.");
      process.exit(1);
    }
    const pundit = new Pundit(config);
    await pundit.comment(marketPda);
  });

program
  .command("analyze")
  .description("Run analysis and print report (no posting)")
  .action(async () => {
    const config = getConfig(program.opts());
    config.dryRun = true;
    const pundit = new Pundit(config);
    const report = await pundit.analyze();

    console.log("\n═══════════════════════════════════════");
    console.log("  ANALYSIS REPORT");
    console.log("═══════════════════════════════════════\n");

    for (const analysis of report.analyses) {
      console.log(`📌 "${analysis.market.question}"`);
      console.log(`   Signal: ${analysis.signal} | Confidence: ${analysis.confidence}% | Favored: ${analysis.favoredOutcome}`);
      console.log(`   Edge: ${(analysis.edge || 0).toFixed(1)}% | Tags: ${analysis.tags.join(", ")}`);
      console.log(`   ${analysis.reasoning.substring(0, 200)}`);
      console.log();
    }

    console.log("═══════════════════════════════════════");
    console.log(`Summary: ${report.summary}`);
    console.log("═══════════════════════════════════════\n");
  });

program
  .command("status")
  .description("Check AgentBook for existing posts")
  .action(async () => {
    const config = getConfig(program.opts());
    const pundit = new Pundit(config);
    const client = pundit.getClient();
    const posts = await client.getPosts(10);

    console.log(`\n📚 Recent AgentBook Posts (${posts.length}):\n`);
    for (const post of posts) {
      console.log(`  #${post.id} by ${post.agent?.agentName || post.walletAddress}`);
      console.log(`  ${post.content?.substring(0, 120)}...`);
      console.log(`  Posted: ${post.createdAt} | Steams: ${post.steams}`);
      console.log();
    }
  });

program.parse();
