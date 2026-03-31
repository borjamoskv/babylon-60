# Contributing to BaoziClaw

## Bounty Program

We pay SOL for working contributions. Each bounty issue has a fixed SOL reward.

### How to Claim a Bounty

1. **Comment on the issue** with your approach (1 paragraph max)
2. **Build the solution** — no approval needed to start working
3. **Post proof** — real output, screenshots, or demo video showing it works on mainnet
4. **Submit a PR** with source code + your Solana wallet address in the PR description
5. **First working submission wins** — no splitting, no reservations

### Rules

- **Proof before merge.** Every bounty requires a working deployed instance. Code review comes after proof of functionality.
- **Real mainnet.** Devnet demos don't count. At least one real mainnet transaction must be demonstrated.
- **No self-referral farming.** If your bounty involves affiliate tracking, affiliate and bettor wallets must be distinct keypairs.
- **Single winner.** First complete submission that meets all acceptance criteria wins. If two people submit simultaneously, the one with better code quality wins.
- **SOL payment within 48h.** After PR merge, bounty is paid to the Solana wallet in your PR description.

### Code Standards

- **TypeScript preferred** for scripts and libraries
- **Python acceptable** for data-heavy skills (follow polyclaw's pattern with uv)
- Follow OpenClaw skill conventions (SKILL.md manifest, scripts/ directory)
- Include error handling — silent failures are not acceptable
- Test with real Solana RPC calls (use a dedicated provider, not public RPC)

### Skill Architecture

```
baozi-openclaw/
├── SKILL.md              # OpenClaw skill manifest (YAML frontmatter + instructions)
├── scripts/              # Executable scripts called by the agent
│   ├── list-markets      # Browse markets
│   ├── get-odds          # Get probabilities
│   ├── place-bet         # Execute trades
│   ├── create-market     # Create Lab markets
│   └── ...
├── lib/                  # Shared modules
│   ├── baozi-client.ts   # RPC + transaction logic
│   └── borsh-parser.ts   # On-chain data parsing
├── references/           # API docs, IDL excerpts for agent context
└── tests/                # Integration tests
```

### Getting Started

1. Fork this repo
2. Install OpenClaw: https://docs.openclaw.ai
3. Set environment variables (`SOLANA_RPC_URL`, `SOLANA_PRIVATE_KEY`)
4. Install the skill locally: `openclaw skill install .`
5. Test: "List active prediction markets on Baozi"

### Resources

- [OpenClaw Skill Docs](https://docs.openclaw.ai/tools/skills)
- [Baozi MCP Server](https://github.com/bolivian-peru/baozi-mcp) — 68 tools (reference implementation)
- [Baozi IDL](https://github.com/bolivian-peru/baozi-mcp/tree/main/src) — On-chain program interface
- [polyclaw](https://github.com/nicejuice-xyz/polyclaw) — Polymarket skill (architectural reference)
- [Baozi.bet](https://baozi.bet) — The platform

### Questions?

Open an issue or reach out on [Telegram](https://t.me/baozibet).
