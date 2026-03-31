/**
 * Baozi Market Factory — Autonomous Market Creation Service
 *
 * Monitors news feeds, crypto prices, and event calendars to auto-create
 * prediction markets on Baozi. Earns 0.5% creator fees on all volume.
 *
 * Bounty #3: https://github.com/bolivian-peru/baozi-openclaw/issues/3
 *
 * Schedule:
 * - Every 30 min: Scan news feeds for market-worthy events
 * - Every 6 hours: Check event calendars, generate curated markets
 * - Every 1 hour: Check for markets needing resolution
 * - Continuous: Track volumes and fees
 */
import { detectMarketOpportunities, MarketProposal } from './news-detector';
import { createLabMarket, getWalletBalance, canAffordMarketCreation } from './market-creator';
import { filterDuplicates } from './duplicate-checker';
import { checkAndResolveMarkets } from './market-resolver';
import { getTotalStats, getCategoryStats, getAllMarkets } from './tracker';
import { config } from './config';

// =============================================================================
// MARKET CREATION LOOP
// =============================================================================

let marketsCreatedToday = 0;
const MAX_MARKETS_PER_DAY = 5; // Conservative limit to preserve SOL balance

async function runMarketCreation(): Promise<void> {
  const timestamp = new Date().toISOString().replace('T', ' ').split('.')[0];
  console.log(`\n${'='.repeat(70)}`);
  console.log(`[Market Factory — ${timestamp}]`);
  console.log(`${'='.repeat(70)}`);

  // Check wallet balance
  const balance = await getWalletBalance();
  console.log(`💰 Wallet balance: ${balance.toFixed(4)} SOL`);

  if (!(await canAffordMarketCreation())) {
    console.log('⚠️ Insufficient balance for market creation. Skipping this cycle.');
    return;
  }

  if (marketsCreatedToday >= MAX_MARKETS_PER_DAY) {
    console.log(`📊 Daily limit reached (${marketsCreatedToday}/${MAX_MARKETS_PER_DAY}). Skipping creation.`);
    return;
  }

  // Detect opportunities
  const proposals = await detectMarketOpportunities();

  if (proposals.length === 0) {
    console.log('📭 No new market opportunities detected this cycle.');
    return;
  }

  // Filter duplicates against live Baozi markets
  const unique = await filterDuplicates(proposals) as MarketProposal[];
  console.log(`\n📋 ${unique.length} unique proposals after dedup (from ${proposals.length} raw)`);

  // Create markets (up to daily limit)
  const remaining = MAX_MARKETS_PER_DAY - marketsCreatedToday;
  const toCreate = unique.slice(0, remaining);

  for (const proposal of toCreate) {
    console.log(`\n🏗️ Creating market: "${proposal.question}"`);
    console.log(`   Category: ${proposal.category} | Source: ${proposal.source}`);
    console.log(`   Closing: ${proposal.closingTime.toISOString()}`);

    const result = await createLabMarket(proposal);

    if (result.success) {
      marketsCreatedToday++;
      console.log(`   ✅ Created! PDA: ${result.marketPda} | TX: ${result.txSignature}`);

      // Small delay between creations to avoid RPC rate limits
      await new Promise(r => setTimeout(r, 5000));
    } else {
      console.log(`   ❌ Failed: ${result.error}`);
      // If we get a program error, don't try more this cycle
      if (result.error?.includes('custom program error')) {
        console.log('   ⛔ Program error — stopping creation for this cycle');
        break;
      }
    }
  }
}

// =============================================================================
// STATS REPORTING
// =============================================================================

function printDailySummary(): void {
  const stats = getTotalStats();
  const categories = getCategoryStats();

  console.log(`\n${'='.repeat(70)}`);
  console.log(`📊 Market Factory Summary`);
  console.log(`${'='.repeat(70)}`);
  console.log(`  Markets created (total): ${stats.markets}`);
  console.log(`  Markets resolved:        ${stats.resolved}`);
  console.log(`  Total volume:            ${stats.volume.toFixed(4)} SOL`);
  console.log(`  Creator fees earned:     ${stats.fees.toFixed(4)} SOL`);

  if (categories.length > 0) {
    console.log(`\n  Category Performance:`);
    for (const cat of categories) {
      console.log(`    ${cat.category}: ${cat.markets_created} markets, ${cat.total_volume_sol.toFixed(4)} SOL volume, ${cat.total_fees_sol.toFixed(4)} SOL fees`);
    }
    console.log(`  Best category: ${categories[0].category} (${categories[0].total_volume_sol.toFixed(4)} SOL)`);
  }
}

// =============================================================================
// MAIN LOOP
// =============================================================================

async function main(): Promise<void> {
  console.log('🏭 Baozi Market Factory starting...');
  console.log(`   Wallet: ${config.walletAddress}`);
  console.log(`   RPC: ${config.rpcEndpoint}`);
  console.log(`   Baozi API: ${config.apiUrl}`);
  console.log(`   News scan interval: ${config.newsScanIntervalMs / 60000} min`);
  console.log(`   Resolution check interval: ${config.resolutionCheckIntervalMs / 60000} min`);

  // Validate private key
  if (!config.privateKey) {
    console.error('❌ PRIVATE_KEY environment variable not set');
    process.exit(1);
  }

  // Initial run
  await runMarketCreation();

  // Schedule recurring tasks
  // News scan every 30 minutes
  setInterval(async () => {
    try {
      await runMarketCreation();
    } catch (err: any) {
      console.error(`Market creation error: ${err.message}`);
    }
  }, config.newsScanIntervalMs);

  // Resolution check every hour
  setInterval(async () => {
    try {
      await checkAndResolveMarkets();
    } catch (err: any) {
      console.error(`Resolution check error: ${err.message}`);
    }
  }, config.resolutionCheckIntervalMs);

  // Daily summary every 24 hours
  setInterval(() => {
    printDailySummary();
    marketsCreatedToday = 0; // Reset daily counter
  }, 24 * 60 * 60 * 1000);

  // Also print summary every 6 hours
  setInterval(() => {
    printDailySummary();
  }, 6 * 60 * 60 * 1000);

  console.log('\n✅ Market Factory is running. Press Ctrl+C to stop.\n');

  // Keep process alive
  process.on('SIGTERM', () => {
    console.log('Shutting down Market Factory...');
    printDailySummary();
    process.exit(0);
  });

  process.on('SIGINT', () => {
    console.log('Shutting down Market Factory...');
    printDailySummary();
    process.exit(0);
  });
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
