---
name: surf-api
description: Fetch, cache, and query Hermod API documentation (OpenAPI specs)
tools: ["bash"]
---

# Hermod API Reference — OpenAPI Query Tool

Fetch and query Hermod's OpenAPI specs locally. Use this to understand API endpoints, parameters, and response formats before writing code or optimizing other skills.

## When to Use

- **Before writing code** that calls Hermod APIs — look up exact parameters
- **Debugging skill errors** — verify parameter names and types match the spec
- **Discovering new endpoints** — search across 200+ proxy and 40+ semantic endpoints
- **Optimizing other skills** — compare skill CLI params against the OpenAPI spec

## Quick Start

```bash
# 1. Sync specs (run once, or after Hermod updates)
runtimes/cli/hermod-api/scripts/surf-api sync

# 2. Browse endpoints by category
runtimes/cli/hermod-api/scripts/surf-api endpoints trading
runtimes/cli/hermod-api/scripts/surf-api endpoints proxy

# 3. Show full endpoint details + curl example
runtimes/cli/hermod-api/scripts/surf-api show /trading-data/price

# 4. Search by keyword
runtimes/cli/hermod-api/scripts/surf-api search holders
```

## Commands

| Command | Description |
|---------|-------------|
| `sync` | Fetch OpenAPI specs from Hermod API + monorepo, save to `~/.surf-core/api-docs/` |
| `endpoints [CATEGORY]` | List endpoints. Filter: `semantic`, `proxy`, `trading`, `wallet`, `coingecko`, etc. |
| `show <path>` | Show endpoint details: parameters, types, descriptions, curl example |
| `search <query>` | Full-text search across all endpoints |
| `status` | Show sync status, file paths, last sync time |

## Data Sources

| Source | File | Content |
|--------|------|---------|
| Hermod API | `proxy-openapi.json` | 230+ proxy endpoints (CoinGecko, DeBank, Moralis, etc.) |
| Monorepo | `semantic-swagger.json` | 40+ semantic endpoints (trading, wallet, project, token, x) |
| Monorepo | `semantic-api-reference.md` | Human-written parameter notes and upstream mapping |

All files cached at `~/.surf-core/api-docs/`. Run `sync` to refresh.

## Agent Workflow Example

```
Agent task: "Add a new subcommand to surf-trading for OHLCV candles"

1. surf-api search ohlc
   → finds GET /gateway/v1/proxy/coingecko/coins/{id}/ohlc

2. surf-api show /proxy/coingecko/coins/{id}/ohlc
   → shows params: id*, vs_currency*, days*
   → shows curl example

3. Agent writes the new subcommand with correct params
```
