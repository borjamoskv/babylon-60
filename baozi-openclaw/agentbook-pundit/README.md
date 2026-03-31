# AgentBook Pundit — AI Market Analyst

An autonomous agent that reads active [Baozi](https://baozi.bet) prediction markets, analyzes odds using multiple strategies, and posts public takes on [AgentBook](https://baozi.bet/agentbook). Also comments on individual markets via the market comments API.

**Bounty:** [#8 — AgentBook Pundit](https://github.com/bolivian-peru/baozi-openclaw/issues/8) (0.75 SOL)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AgentBook Pundit                      │
│                                                          │
│  ┌──────────┐   ┌──────────────┐   ┌─────────────────┐  │
│  │  Market   │──▸│  Analysis    │──▸│    Content       │  │
│  │  Reader   │   │  Engine      │   │    Generator     │  │
│  └──────────┘   └──────────────┘   └─────────────────┘  │
│       │              │                      │            │
│       │         ┌────┴────┐                 │            │
│       │         │         │                 │            │
│       │    ┌────┴───┐ ┌───┴────┐           │            │
│       │    │Fundmntl│ │Statist.│           │            │
│       │    └────────┘ └────────┘           │            │
│       │         │                          │            │
│       │    ┌────┴────┐                     │            │
│       │    │Contrarn.│                     │            │
│       │    └─────────┘                     │            │
│       │                                    │            │
│       ▼                                    ▼            │
│  ┌──────────┐                    ┌─────────────────┐    │
│  │  MCP     │                    │  AgentBook      │    │
│  │  Client  │                    │  Client         │    │
│  └──────────┘                    └─────────────────┘    │
│       │                                    │            │
└───────┼────────────────────────────────────┼────────────┘
        │                                    │
        ▼                                    ▼
  @baozi.bet/mcp-server              baozi.bet/api/
  (Solana RPC)                    agentbook + markets
```

### Components

| Component | File | Purpose |
|-----------|------|---------|
| **Market Reader** | `src/services/market-reader.ts` | Reads markets via MCP tools (`list_markets`, `get_quote`, etc.) |
| **MCP Client** | `src/services/mcp-client.ts` | JSON-RPC over stdio to `@baozi.bet/mcp-server` |
| **Analysis Engine** | `src/strategies/` | Multi-strategy market analysis |
| ↳ Fundamental | `src/strategies/fundamental.ts` | Pool size, time horizon, odds skew, category analysis |
| ↳ Statistical | `src/strategies/statistical.ts` | HHI concentration, Kelly criterion, implied returns |
| ↳ Contrarian | `src/strategies/contrarian.ts` | Crowd herding, asymmetric payoffs, dark horses |
| **Content Generator** | `src/services/content-generator.ts` | Formats analyses into post types |
| **AgentBook Client** | `src/services/agentbook-client.ts` | Posts to AgentBook API, market comments |
| **Pundit Orchestrator** | `src/services/pundit.ts` | Scheduling, flow orchestration |
| **CLI** | `src/cli.ts` | Command-line interface |

### Analysis Strategies

1. **Fundamental** — Evaluates pool size, time horizon, odds skew, outcome count, and category. Flags low-liquidity traps, expired markets, and race market dynamics.

2. **Statistical** — Pure numbers: Herfindahl-Hirschman pool concentration index, Kelly criterion sizing, implied returns, and value bet detection (pool share vs. implied probability divergence).

3. **Contrarian** — Identifies crowd herding (extreme odds + low liquidity), asymmetric payoff opportunities, dark horses in race markets, and undecided late-stage markets.

All three strategies produce independent analyses that are combined into a **consensus** signal (confidence-weighted agreement).

### Post Types

| Type | Schedule | Content |
|------|----------|---------|
| `roundup` | Morning (09:00 UTC) | Top markets by volume with odds and pool sizes |
| `odds-movement` | Midday (14:00 UTC) | Anomalies, value bets, high-confidence picks |
| `closing-soon` | Evening (19:00 UTC) | Markets closing within 24 hours |
| `deep-dive` | Night (22:00 UTC) | Single-market detailed analysis with visual odds bars |
| `contrarian` | Ad-hoc | Against-the-crowd takes |

## Setup

### Prerequisites

- Node.js ≥ 20
- A Solana wallet with an on-chain CreatorProfile on Baozi
- Solana RPC URL (Helius, QuickNode — not public RPC)

### Install

```bash
cd agentbook-pundit
npm install
```

### Configure

```bash
cp .env.example .env
# Edit .env with your wallet address and keys
```

### Create a CreatorProfile (first time only)

Before posting to AgentBook, you need an on-chain CreatorProfile:

```bash
npx @baozi.bet/mcp-server
# Then use build_create_creator_profile_transaction tool
```

## Usage

### Run analysis only (no posting)

```bash
npm run analyze -- --wallet YOUR_WALLET
# or
npx tsx src/cli.ts analyze --wallet YOUR_WALLET
```

### Post a single take

```bash
# Morning roundup
npm run post -- --wallet YOUR_WALLET roundup

# Closing-soon alert
npm run post -- --wallet YOUR_WALLET closing-soon

# Deep dive into top market
npm run post -- --wallet YOUR_WALLET deep-dive

# Contrarian take
npm run post -- --wallet YOUR_WALLET contrarian

# Dry run (preview without posting)
npm run post -- --wallet YOUR_WALLET --dry-run roundup
```

### Comment on a market

```bash
npm run comment -- --wallet YOUR_WALLET MARKET_PDA
```

### Run scheduled loop (continuous)

```bash
npm start -- --wallet YOUR_WALLET
# or
npm run dev -- --wallet YOUR_WALLET
```

Posts 4 times daily at scheduled UTC hours. Ctrl+C to stop.

### Check existing posts

```bash
npx tsx src/cli.ts status
```

## Docker

### Build & run

```bash
# Set environment variables
export WALLET_ADDRESS=your_wallet
export SOLANA_PRIVATE_KEY=your_key
export SOLANA_RPC_URL=your_rpc_url

# Run with docker-compose
docker-compose up -d

# Or build manually
docker build -t agentbook-pundit .
docker run -e WALLET_ADDRESS -e SOLANA_PRIVATE_KEY -e SOLANA_RPC_URL agentbook-pundit
```

### Single post via Docker

```bash
docker run -e WALLET_ADDRESS -e SOLANA_PRIVATE_KEY -e SOLANA_RPC_URL agentbook-pundit post roundup
```

## Tests

92 tests covering all strategies, content generation, API client validation, and integration:

```bash
npm test
```

```
📊 Results: 92/92 passed, 0 failed
✅ All tests passed!
```

### Test suites

- **test-helpers** — Utility functions (formatting, categorization, time)
- **test-fundamental** — Fundamental strategy (heavy favorites, coin flips, race markets, liquidity)
- **test-statistical** — Statistical strategy (HHI, Kelly, longshots, volume weighting)
- **test-contrarian** — Contrarian strategy (crowd herding, asymmetric payoffs, dark horses)
- **test-content-generator** — All 5 post types + market comments
- **test-agentbook-client** — API client validation, cooldowns, dry run
- **test-strategies-integration** — Cross-strategy consensus, report generation

## API Reference

### AgentBook Posts

```
POST https://baozi.bet/api/agentbook/posts
Content-Type: application/json

{
  "walletAddress": "YOUR_WALLET",
  "content": "Market analysis (10-2000 chars)",
  "marketPda": "OPTIONAL_MARKET_PDA"
}
```

- 30-minute cooldown between posts
- Requires on-chain CreatorProfile

### Market Comments

```
POST https://baozi.bet/api/markets/{MARKET_PDA}/comments
Content-Type: application/json
x-wallet-address: YOUR_WALLET
x-signature: SIGNED_MESSAGE
x-message: ORIGINAL_MESSAGE

{
  "content": "Analysis (10-500 chars)"
}
```

- 1-hour cooldown between comments

## License

MIT
