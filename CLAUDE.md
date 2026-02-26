# CLAUDE.md — surf-core

surf-core is an Agent Skills repository following the [Agent Skills Open Standard](https://github.com/anthropics/agent-skills). It provides a complete Crypto data toolchain via the Hermod API Gateway, compatible with Claude Code, OpenAI Codex, GitHub Copilot, Gemini CLI, and other agent platforms.

## Repository Structure

```
surf-core/
├── knowledge/            # Domain knowledge (endpoints, patterns, responses)
│   ├── auth/             # Authentication & session docs
│   ├── market/           # Market data (prices, futures, options, indicators, ETF)
│   ├── project/          # Project data (overview, TVL, revenue, fees, users)
│   ├── token/            # Token data (holders, transfers, exchange flows)
│   ├── wallet/           # Wallet data (balance, holdings, tx history, labels)
│   ├── social/           # Social & X/Twitter data (sentiment, users, tweets)
│   ├── news/             # News data (search, feed, AI summaries)
│   ├── web/              # Web data (search, fetch)
│   └── onchain/          # On-chain SQL (ClickHouse databases, examples)
├── runtimes/             # Executable skill implementations
│   ├── cli/              # Bash CLI skills
│   │   ├── lib/          # Shared shell utilities (config.sh, http.sh)
│   │   ├── login/        # Google Sign-In, session management
│   │   ├── hermod-api/   # API reference — query OpenAPI specs (273 endpoints)
│   │   ├── market/       # Market data (prices, charts, exchanges)
│   │   ├── news/         # News search with semantic ranking
│   │   ├── onchain/      # OnchainSQL (ClickHouse on-chain queries)
│   │   ├── project/      # Project data (overview, TVL, revenue, fees)
│   │   ├── token/        # Token data (holders, transfers, exchange flows)
│   │   ├── wallet/       # Wallet data (balance, holdings, tx history)
│   │   └── social/       # Social & X/Twitter data (search, users, tweets)
│   └── http/             # HTTP-based skill implementations
│       └── market/       # Market data via HTTP
├── CLAUDE.md
├── README.md
└── SKILL-SPEC.md
```

## Getting Started

```bash
# 1. Login (opens browser, one-click Google Sign-In)
runtimes/cli/login/scripts/surf-session login

# 2. Verify connectivity
runtimes/cli/login/scripts/surf-session check

# 3. Use any data skill
runtimes/cli/market/scripts/surf-market price --ids bitcoin --vs usd
```

Session persists to `~/.surf-core/session.json` (access_token 1h + refresh_token 30d). Login once, use for 30 days.

## Skill Specification

**All skill changes MUST follow `SKILL-SPEC.md`.** Key rules:

1. **Error messages MUST list valid options** — agents retry-loop without this
   - `"Unknown flag: $1. Valid: --address, --chain, --limit"`
   - `"Unknown command: $1. Available: price, future, cg-markets, ..."`
2. **Commands returning lists MUST support `--limit`** — agents lose context on large responses
3. **SKILL.md examples MUST be copy-pasteable** — agents run them verbatim, no `<PLACEHOLDER>`
4. **usage() MUST be valid JSON** with credit cost per subcommand
5. **Every skill MUST have `--check-setup`**

Run the checklist in `SKILL-SPEC.md` before merging any skill PR.

## CLI Convention

```bash
runtimes/cli/<skill>/scripts/<cmd> --check-setup       # Verify config
runtimes/cli/<skill>/scripts/<cmd> <subcommand> [args]  # Execute
```

All output is JSON. Errors return `{"error": "..."}` with non-zero exit code.

## Hermod API

All data flows through Hermod (`/gateway/v1/`). Auth: `Authorization: Bearer <token>`.

### Standard API Routes

| Domain | Path Prefix | Credit Cost |
|--------|-------------|-------------|
| Market | `/gateway/v1/market/` | 1 |
| Project | `/gateway/v1/project/` | 1 |
| Token | `/gateway/v1/token/` | 1 |
| Wallet | `/gateway/v1/wallet/` | 1-2 |
| Social | `/gateway/v1/social/` | 1 |
| News | `/gateway/v1/news/` | 1 |
| Web | `/gateway/v1/web/` | 1 |
| Onchain | `/gateway/v1/onchain/` | 5 |

### Proxy API Routes

Proxy routes forward to upstream APIs with automatic API key injection: `/gateway/v1/proxy/{service}/...`

| Service | Upstream | Credit | Use Case |
|---------|----------|--------|----------|
| coingecko | CoinGecko Pro | 2 | Prices, market data, trending |
| coinglass | CoinGlass | 3 | Futures, OI, funding, liquidations |
| taapi | TAAPI.io | 2 | 200+ technical indicators |
| cryptoquant | CryptoQuant | 3 | Exchange flows, SOPR, NUPL |
| sosovalue | SosoValue | 2 | BTC/ETH ETF flows |
| tt | Token Terminal | 2 | Protocol revenue, fees, TVL, users |
| debank | DeBank Pro | 5 | Cross-chain portfolio, DeFi positions |
| etherscan | Etherscan V2 | 4 | EVM tx history, contract ABI |
| moralis | Moralis | 2 | Token holders, balances, transfers |
| solscan | Solscan Pro | 4 | Solana txs, tokens, accounts |
| alchemy-* | Alchemy (eth/base/arb/opt/polygon/solana) | 1 | JSON-RPC, token balances |

### API Reference (hermod-api)

```bash
runtimes/cli/hermod-api/scripts/surf-api sync              # Fetch latest specs → ~/.surf-core/api-docs/
runtimes/cli/hermod-api/scripts/surf-api endpoints trading  # List trading endpoints
runtimes/cli/hermod-api/scripts/surf-api show /wallet/balance  # Full params + curl example
runtimes/cli/hermod-api/scripts/surf-api search holders     # Search across all 273 endpoints
```
