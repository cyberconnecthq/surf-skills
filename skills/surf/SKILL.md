---
name: surf
description: >-
  Access the Surf crypto data API — for research, investigation, or fetching live data.
  Uses the surf CLI directly for querying crypto data (market prices, wallets, social, DeFi,
  tokens, prediction markets, on-chain, exchange, news).
  Use whenever the user needs crypto data, asks about prices/wallets/tokens/DeFi, wants
  to investigate on-chain activity, or is building something that consumes crypto data —
  even if they don't say "surf" explicitly.
tools:
  - bash
---

# Surf Data API

`surf` is a global CLI for querying crypto data. Run it directly (NOT via `npx surf`).

**CLI flags use kebab-case** (e.g. `--time-range`, `--token-address`), NOT snake_case.

## Setup

Install the Surf CLI:

```bash
curl -fsSL https://agent.asksurf.ai/cli/releases/install.sh | sh
surf login
```

## CLI Usage

### Discovery

```bash
surf sync                       # Refresh API spec cache — always run first
surf list-operations            # All available commands with params
surf list-operations | grep <domain>  # Filter by domain
surf <command> --help           # Full params, enums, defaults, response schema
```

Always run `surf sync` before discovery. Always check `--help` before calling a
command — it shows every flag with its type, enum values, and defaults.

### Getting Data

```bash
surf market-price --symbol BTC -o json -f body.data
surf wallet-detail --address 0x... -o json -f body.data
surf social-user --handle vitalikbuterin -o json -f body.data
```

- `-o json` → JSON output
- `-f body.data` → extract just the data array/object (skip envelope)
- `-f body.data[0]` → first item only
- `-f body.data -r` → raw strings, not escaped
- `-f body.meta` → metadata (credits used, pagination info)

### Domain Guide

| Need | Grep for |
|------|----------|
| Prices, market cap, rankings, fear & greed | `market` |
| Futures, options, liquidations | `market` |
| Technical indicators (RSI, MACD, Bollinger) | `market` |
| On-chain indicators (NUPL, SOPR) | `market` |
| Wallet portfolio, balances, transfers | `wallet` |
| DeFi positions (Aave, Compound, etc.) | `wallet` |
| Twitter/X profiles, posts, followers | `social` |
| Mindshare, sentiment, smart followers | `social` |
| Token holders, DEX trades, unlocks | `token` |
| Project info, DeFi TVL, protocol metrics | `project` |
| Order books, candlesticks, funding rates | `exchange` |
| VC funds, portfolios, rankings | `fund` |
| Transaction lookup, gas prices, SQL | `onchain` |
| Kalshi binary markets | `kalshi` |
| Polymarket prediction markets | `polymarket` |
| Cross-platform prediction metrics | `prediction-market` |
| News feed and articles | `news` |
| Cross-domain entity search | `search` |
| Fetch/parse any URL | `web` |

### Gotchas

Things `--help` won't tell you:

- **Never use `-q` for search.** `-q` is a global flag (not the `--q` search parameter). Always use `--q` (double dash).
- **Chains require canonical long-form names.** `eth` → `ethereum`, `sol` → `solana`, `matic` → `polygon`, `avax` → `avalanche`, `arb` → `arbitrum`, `op` → `optimism`, `ftm` → `fantom`, `bnb` → `bsc`.
- **POST endpoints (`onchain-sql`, `onchain-structured-query`) take JSON on stdin.** Pipe JSON: `echo '{"sql":"SELECT ..."}' | surf onchain-sql`. Always filter on `block_date` — it's the partition key.
- **Ignore `--rsh-*` internal flags in `--help` output.** Only the command-specific flags matter.

### Troubleshooting

- **Auth errors**: Run `surf refresh` to renew an expired token, or `surf login` to re-authenticate
- **Unknown command**: Run `surf sync` to update schema, then `surf list-operations` to verify
- **Empty results**: Check `--help` for required params and valid enum values

---

## API Reference

For building apps that call the Surf API directly (without the SDK).

### API Conventions

```
Base URL:  https://api.asksurf.ai/gateway/v1
Auth:      Authorization: Bearer <token>
```

**URL Mapping** — command name → API path:
```
market-price          →  GET /market/price
social-user-posts     →  GET /social/user-posts
onchain-sql           →  POST /onchain/sql
```

Known domain prefixes: `market`, `wallet`, `social`, `token`, `project`, `fund`,
`onchain`, `news`, `exchange`, `search`, `web`, `kalshi`, `polymarket`,
`prediction-market`.

### Response Envelope

```json
{ "data": [...items], "meta": { "credits_used": 1, "cached": false } }
```

Variants:
- **Object response** (detail endpoints): `data` is an object, not array
- **Offset-paginated**: `meta` includes `total`, `limit`, `offset`
- **Cursor-paginated**: `meta` includes `has_more`, `next_cursor`

### Reading `--help` Schema Notation

| Schema notation | Meaning |
|-----------------|---------|
| `(string)` | string |
| `(integer format:int64)` | integer |
| `(number format:double)` | float |
| `(boolean)` | boolean |
| `field*:` | required |
| `field:` | optional |
| `enum:"a","b","c"` | constrained values |
| `default:"30d"` | default value |
| `min:1 max:100` | range constraint |

### Detecting Pagination from `--help`

- **Cursor**: has `--cursor` param AND response meta has `has_more` + `next_cursor`
- **Offset**: has `--limit` + `--offset` params AND response meta has `total`
- **None**: neither pattern

---

## API Feedback

When a surf command fails, returns confusing results, or the API doesn't support
something the user naturally expects, log a suggestion:

```bash
mkdir -p ~/.surf/api-feedback
```

Write one file per issue: `~/.surf/api-feedback/<YYYY-MM-DD>-<slug>.md`

```markdown
# <Short title>

**Command tried:** `surf <command> --flags`
**What the user wanted:** <what they were trying to accomplish>
**What happened:** <error message, empty results, or confusing behavior>

## Suggested API fix

<How the API could change to make this work naturally>
```
