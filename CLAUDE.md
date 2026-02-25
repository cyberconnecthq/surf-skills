# CLAUDE.md — surf-core

surf-core is an Agent Skills repository following the [Agent Skills Open Standard](https://github.com/anthropics/agent-skills). It provides a complete Crypto data toolchain via the Hermod API Gateway, compatible with Claude Code, OpenAI Codex, GitHub Copilot, Gemini CLI, and other agent platforms.

## Repository Structure

```
surf-core/
├── surf-login/           # ** PREREQUISITE ** — Google Sign-In, session management
├── surf-hermod-api/      # API reference — fetch, cache, query OpenAPI specs (273 endpoints)
├── surf-trading-data/    # Trading data (price, futures, options, liquidation, indicators)
├── surf-wallet-data/     # Wallet data (balance, holdings, tx history, labels)
├── surf-project-data/    # Project data (overview, TVL, revenue, fees, users)
├── surf-token-data/      # Token data (holders, transfers, exchange flows)
├── surf-onchain-sql/     # OnchainSQL (ClickHouse on-chain data queries)
├── surf-x-data/          # X/Twitter data (search, users, tweets)
├── lib/                  # Shared shell utilities (config loader, HTTP wrapper)
├── CLAUDE.md
└── README.md
```

## Getting Started

```bash
# 1. Login (opens browser, one-click Google Sign-In)
surf-login/scripts/surf-session login

# 2. Verify connectivity
surf-login/scripts/surf-session check

# 3. Use any data skill
surf-trading-data/scripts/surf-trading price --ids bitcoin --vs usd
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
<skill>/scripts/<cmd> --check-setup       # Verify config
<skill>/scripts/<cmd> <subcommand> [args]  # Execute
```

All output is JSON. Errors return `{"error": "..."}` with non-zero exit code.

## Hermod API

All data flows through Hermod (`/gateway/v1/`). Auth: `Authorization: Bearer <token>`.

### Semantic API Routes

| Domain | Path Prefix | Credit Cost |
|--------|-------------|-------------|
| Trading Data | `/gateway/v1/trading-data/` | 1 |
| Project Data | `/gateway/v1/project/` | 1 |
| Wallet Data | `/gateway/v1/wallet/` | 1-2 |
| Token Data | `/gateway/v1/token-data/` | 1 |
| OnchainSQL | `/gateway/v1/onchain/query` | 5 |
| X/Twitter | `/gateway/v1/x/` | 2-3 |

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

### API Reference (surf-hermod-api)

```bash
surf-hermod-api/scripts/surf-api sync              # Fetch latest specs → ~/.surf-core/api-docs/
surf-hermod-api/scripts/surf-api endpoints trading  # List trading endpoints
surf-hermod-api/scripts/surf-api show /wallet/balance  # Full params + curl example
surf-hermod-api/scripts/surf-api search holders     # Search across all 273 endpoints
```
