# CLAUDE.md — surf-core

surf-core is the Agent core capability repository. It provides Skills and CLI tools for Claude Code and other agent frameworks, giving them a complete Crypto data toolchain via the Hermod API Gateway.

## Architecture

```
surf-core/
├── skills/
│   ├── surf-hermod-session/ # ** PREREQUISITE ** — connect to Hermod, manage JWT session
│   ├── surf-trading-data/   # Trading data (price, futures, options, liquidation, indicators)
│   ├── surf-wallet-data/    # Wallet data (balance, holdings, tx history, labels)
│   ├── surf-project-data/   # Project data (overview, TVL, revenue, fees, users)
│   ├── surf-token-data/     # Token data (holders, transfers, exchange flows)
│   ├── surf-onchain-sql/    # OnchainSQL (ClickHouse on-chain data queries)
│   └── surf-x-data/         # X/Twitter data (search, users, tweets)
├── lib/                     # Shared shell utilities
│   ├── config.sh            # Config loader (env → ~/.surf-core/session.json fallback)
│   └── http.sh              # curl wrapper (unified headers, error handling)
└── CLAUDE.md
```

## Getting Started (Session Setup)

**Before using any data skill, you must configure a Hermod session:**

```bash
# 1. Configure session with JWT (issued by Muninn)
skills/surf-hermod-session/scripts/surf-session configure --token <JWT>

# 2. Verify connectivity
skills/surf-hermod-session/scripts/surf-session check

# 3. Now use any data skill
skills/surf-trading-data/scripts/surf-trading price --symbol BTC
```

Session is persisted to `~/.surf-core/session.json` — all skills auto-load from this file. Environment variables (`HERMOD_TOKEN`, `HERMOD_URL`) override the file if set.

## Design Principles

- **Agent-first**: All CLI output is JSON — structured, parseable, pipeable
- **Zero dependencies**: Bash + curl only, no installation required
- **Simple & composable**: Single-responsibility commands, no interactive prompts
- **Co-located**: CLI scripts live inside their Skill directories
- **Session-first**: Configure once, use everywhere — no per-command auth

## CLI Convention

Every skill CLI follows the same pattern:

```bash
skills/<skill>/scripts/<cmd> --check-setup     # Verify config
skills/<skill>/scripts/<cmd> <subcommand> [args]  # Execute
```

All output is JSON. Errors return `{"error": "..."}` with non-zero exit code.

## Hermod API

All data flows through Hermod (`/gateway/v1/`). Auth: `Authorization: Bearer <token>`.

### Semantic API Routes (Fixed Endpoints)

| Domain | Path Prefix | Credit Cost |
|--------|-------------|-------------|
| Trading Data | `/gateway/v1/trading-data/` | 1 |
| Project Data | `/gateway/v1/project/` | 1 |
| Wallet Data | `/gateway/v1/wallet/` | 1-2 |
| Token Data | `/gateway/v1/token-data/` | 1 |
| OnchainSQL | `/gateway/v1/onchain/query` | 5 |
| X/Twitter | `/gateway/v1/x/` | 2-3 |

### Proxy API Routes (Upstream Passthrough)

Proxy routes forward to upstream APIs with automatic API key injection: `/gateway/v1/proxy/{service}/...`

| Service | Proxy Path | Upstream | Credit Cost | Use Case |
|---------|------------|----------|-------------|----------|
| coingecko | `/proxy/coingecko/` | CoinGecko Pro | 2 | Prices, market data, trending |
| coinglass | `/proxy/coinglass/` | CoinGlass | 3 | Futures, OI, funding, liquidations |
| taapi | `/proxy/taapi/` | TAAPI.io | 2 | 200+ technical indicators |
| cryptoquant | `/proxy/cryptoquant/` | CryptoQuant | 3 | Exchange flows, SOPR, NUPL |
| sosovalue | `/proxy/sosovalue/` | SosoValue | 2 | BTC/ETH ETF flows |
| tt | `/proxy/tt/` | Token Terminal | 2 | Protocol revenue, fees, TVL, users |
| debank | `/proxy/debank/` | DeBank Pro | 5 | Cross-chain portfolio, DeFi positions |
| etherscan | `/proxy/etherscan/` | Etherscan V2 | 4 | EVM tx history, contract ABI |
| moralis | `/proxy/moralis/` | Moralis | 2 | Token holders, balances, transfers |
| solscan | `/proxy/solscan/` | Solscan Pro | 4 | Solana txs, tokens, accounts |
| recon | `/proxy/recon/` | Recon (internal) | 1 | Address labels, entity search |
| muninn | `/proxy/muninn/` | Muninn (internal) | 1 | Project search, disambiguation |
| alchemy-eth | `/proxy/alchemy-eth/` | Alchemy Ethereum | 1 | JSON-RPC, token balances |
| alchemy-base | `/proxy/alchemy-base/` | Alchemy Base | 1 | JSON-RPC, token balances |
| alchemy-arb | `/proxy/alchemy-arb/` | Alchemy Arbitrum | 1 | JSON-RPC, token balances |
| alchemy-opt | `/proxy/alchemy-opt/` | Alchemy Optimism | 1 | JSON-RPC, token balances |
| alchemy-polygon | `/proxy/alchemy-polygon/` | Alchemy Polygon | 1 | JSON-RPC, token balances |
| alchemy-solana | `/proxy/alchemy-solana/` | Alchemy Solana | 1 | JSON-RPC |

Each skill's `references/endpoints.md` documents both semantic and proxy endpoints for its domain.
