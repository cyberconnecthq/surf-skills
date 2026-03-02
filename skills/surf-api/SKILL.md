---
name: surf-api
description: Query all Surf/hermod data APIs via restish
tools:
  - bash
---

# Surf Data API (via restish)

Access all hermod data endpoints through `surf`. Commands are auto-generated from the OpenAPI 3.1 spec — no manual wrappers needed.

## Prerequisites

1. Login first (one-time): `surf-session login`
2. `restish` must be installed and configured (run `install.sh` from surf-core root)

## Discovery

```bash
# List all available commands
surf list-operations

# Get detailed help for any command
surf <command> --help
```

## Quick Examples

### Market (15 commands)

```bash
# Get current prices for assets
surf market-price --ids bitcoin,ethereum,solana

# Get top assets by market cap
surf market-top --metric market_cap --limit 10

# Search market assets by keyword
surf market-search --q "layer 2"

# Get trending tokens
surf market-trending
```

### Project (27 commands)

```bash
# Search projects by name or ticker
surf project-search --q uniswap

# Get full project overview
surf project-overview --q bitcoin

# Get project metrics (TVL, volume, etc.)
surf project-metrics --q ethereum --metric tvl
```

### Token (8 commands)

```bash
# Get on-chain token metadata
surf token-info --address 0xdAC17F958D2ee523a2206206994597C13D831ec7 --chain ethereum

# Get top holders for a token
surf token-holders --address 0xdAC17F958D2ee523a2206206994597C13D831ec7 --chain ethereum --limit 20
```

### Wallet (10 commands)

```bash
# Get wallet portfolio balance
surf wallet-balance --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Get wallet token holdings
surf wallet-tokens --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045
```

### Social (8 commands)

```bash
# Search X/Twitter posts
surf social-search --q "bitcoin ETF"

# Get social sentiment for a project
surf social-sentiment --q ethereum
```

### News (5 commands)

```bash
# Get latest crypto news feed
surf news-feed --limit 10

# Search news articles with filters
surf news-search --q "DeFi hack" --sort recency --from 2025-01-01
```

### Web (2 commands)

```bash
# Search the web
surf web-search --q "bitcoin price prediction 2026"

# Fetch and parse a URL
surf web-fetch --url "https://ethereum.org"
```

### Onchain (3 commands)

```bash
# Execute raw SQL on ClickHouse blockchain data (POST)
surf onchain-sql <<< '{"sql": "SELECT * FROM eth_transactions LIMIT 10"}'

# Get transaction details by hash
surf onchain-tx --hash 0xabc123...
```

## Command Naming Convention

Commands are derived from operationId in kebab-case:

| HTTP Route | Command |
|---|---|
| `GET /v1/market/price` | `market-price` |
| `GET /v1/project/search` | `project-search` |
| `POST /v1/onchain/sql` | `onchain-sql` |

## Response Format

All data endpoints return:

```json
{
  "data": [ ... ],
  "meta": {
    "total": 100,
    "limit": 20,
    "offset": 0,
    "credits_used": 1,
    "cached": false
  }
}
```

Errors return:

```json
{
  "error": {
    "code": "not_found",
    "message": "project not found"
  }
}
```

Use `-f` to filter response fields:

```bash
# Get only the data array
surf market-price --ids bitcoin -f body.data

# Output as raw JSON (for piping to jq)
surf market-top --metric market_cap -o json
```

## Common Flags

| Flag | Description |
|---|---|
| `--limit` | Results per page (default 20, max 100) |
| `--offset` | Pagination offset (default 0) |
| `-o json` | Force JSON output format |
| `-f body.data` | Filter to data array only |
| `-v` | Verbose output (debug) |

## Credit Cost per Call

| Domain | Cost | Notes |
|---|---|---|
| Market | 1 | All market endpoints |
| Project | 1 | All project endpoints |
| Token | 1 | All token endpoints |
| Wallet | 1-2 | PnL/history = 2 |
| Social | 1 | All social endpoints |
| News | 1 | All news endpoints |
| Web | 1 | Search and fetch |
| Onchain | 5 | SQL queries are expensive |
| Entity | 0 | Entity resolution is free |

## All Commands Reference

**Entity** (2): `entity-resolve`, `entity-resolve-batch`

**Market** (15): `market-etf`, `market-futures`, `market-indicator`, `market-liquidation`, `market-metric`, `market-options`, `market-prediction`, `market-prediction-detail`, `market-price`, `market-price-metrics`, `market-search`, `market-tge`, `market-top`, `market-trending`, `market-volume`

**Project** (27): `project-contracts`, `project-discover`, `project-discover-fdv`, `project-discover-summary`, `project-discover-tweets`, `project-events`, `project-funding`, `project-listings`, `project-metrics`, `project-mindshare`, `project-mindshare-by-tag`, `project-mindshare-geo`, `project-mindshare-lang`, `project-mindshare-leaderboard`, `project-overview`, `project-search`, `project-smart-followers`, `project-smart-followers-events`, `project-smart-followers-history`, `project-smart-followers-members`, `project-social`, `project-tags`, `project-team`, `project-token-info`, `project-tokenomics`, `project-top`, `project-vc-portfolio`

**Social** (8): `social-follower-geo`, `social-search`, `social-sentiment`, `social-top`, `social-tweets`, `social-user`, `social-user-posts`, `social-user-related`

**Token** (8): `token-holders`, `token-info`, `token-metrics`, `token-search`, `token-top`, `token-top-traders`, `token-transfers`, `token-unlock`

**Wallet** (10): `wallet-balance`, `wallet-history`, `wallet-labels`, `wallet-labels-batch`, `wallet-nft`, `wallet-pnl`, `wallet-search`, `wallet-tokens`, `wallet-top`, `wallet-transfers`

**News** (5): `news-ai`, `news-ai-detail`, `news-feed`, `news-search`, `news-top`

**Web** (2): `web-fetch`, `web-search`

**Onchain** (3): `onchain-sql`, `onchain-structured-query`, `onchain-tx`

**Credit** (3): `me-credit-history`, `me-credit-summary`, `me-rate-limits`

**X Legacy** (4): `x-get-tweets-by-ids`, `x-get-user`, `x-get-user-tweets`, `x-search`

## Troubleshooting

```bash
# Check session status
surf-session check

# Re-login if token expired
surf-session login

# Verify restish can reach the API
surf market-price --ids bitcoin
```
