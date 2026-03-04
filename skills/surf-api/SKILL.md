---
name: surf-api
description: Query all Surf/hermod data APIs via restish
tools:
  - bash
---

# Surf Data API (via restish)

Access all hermod data endpoints through `surf`. Commands are auto-generated from the OpenAPI 3.1 spec — no manual wrappers needed.

## Stale Commands?

If a `surf` command from this doc returns "unknown command", the API may have changed.
Run `bash <surf-core-repo>/bin/surf-update-api` to sync, then re-read this file.

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

### Market (9 commands)

```bash
# Get current prices for assets
surf market-price --ids bitcoin,ethereum,solana

# Get ETF data
surf market-etf

# Get futures data
surf market-futures

# Get DEX volume
surf market-dex-volume
```

### Search (8 commands)

```bash
# Search projects
surf search-project --q uniswap

# Search tokens
surf search-token --q "USDT"

# Search news
surf search-news --q "DeFi hack"

# Search social posts
surf search-social --q "bitcoin ETF"

# Search the web
surf search-web --q "bitcoin price prediction 2026"

# Get top market data
surf search-top-market
```

### Project (4 commands)

```bash
# Get project detail
surf project-detail --q bitcoin

# Get project metrics (TVL, volume, etc.)
surf project-metrics --q ethereum --metric tvl
```

### Token (4 commands)

```bash
# Get on-chain token metadata
surf token-info --address 0xdAC17F958D2ee523a2206206994597C13D831ec7 --chain ethereum

# Get top holders for a token
surf token-holders --address 0xdAC17F958D2ee523a2206206994597C13D831ec7 --chain ethereum --limit 20

# Get DEX trades for a token
surf token-dex-trades --address 0xdAC17F958D2ee523a2206206994597C13D831ec7 --chain ethereum
```

### Wallet (7 commands)

```bash
# Get wallet portfolio balance
surf wallet-balance --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Get wallet token holdings
surf wallet-tokens --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045
```

### Social (3 commands)

```bash
# Get social tweets
surf social-tweets --q "bitcoin ETF"

# Get user profile
surf social-user --handle vitalikbuterin
```

### News (1 command)

```bash
# Get AI-curated news
surf news-ai --limit 10
```

### Web (1 command)

```bash
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
| `GET /v1/search/project` | `search-project` |
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
surf market-price --ids bitcoin -o json
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
| Wallet | 1-2 | History = 2 |
| Social | 1 | All social endpoints |
| News | 1 | All news endpoints |
| Web | 1 | Fetch |
| Onchain | 5 | SQL queries are expensive |
| Search | 1 | All search endpoints |

## All Commands Reference

**Market** (9): `market-dex-volume`, `market-etf`, `market-futures`, `market-indicator`, `market-liquidation`, `market-onchain-indicator`, `market-options`, `market-price`, `market-price-metrics`

**Project** (4): `project-detail`, `project-events`, `project-metrics`, `project-tokenomics`

**Social** (3): `social-tweets`, `social-user`, `social-user-posts`

**Token** (4): `token-dex-trades`, `token-holders`, `token-info`, `token-transfers`

**Wallet** (7): `wallet-balance`, `wallet-history`, `wallet-labels`, `wallet-labels-batch`, `wallet-nft`, `wallet-tokens`, `wallet-transfers`

**News** (1): `news-ai`

**Web** (1): `web-fetch`

**Onchain** (3): `onchain-sql`, `onchain-structured-query`, `onchain-tx`

**Credit** (5): `me-booster-packages`, `me-credit-balance`, `me-credit-history`, `me-credit-summary`, `me-rate-limits`

**Search** (8): `search-news`, `search-project`, `search-social`, `search-token`, `search-top-market`, `search-top-news`, `search-wallet`, `search-web`

## Troubleshooting

```bash
# Check session status
surf-session check

# Re-login if token expired
surf-session login

# Verify restish can reach the API
surf market-price --ids bitcoin
```
