# surf-skills — Agent Skills for the Surf Data Platform

Give your AI coding agent direct access to crypto market data, wallet intelligence, social analytics, prediction markets, and on-chain data — across 40+ blockchains and 200+ data sources.

> **[Full Documentation →](https://docs.asksurf.ai)**

## Install

```bash
npx skills add asksurf-ai/surf-skills --skill surf
```

Works with any agent that supports the [skills protocol](https://skills.sh) — Claude Code, Codex, and more.

### Prerequisites

Install the Surf CLI following the guide at [agents.asksurf.ai/docs/cli](https://agents.asksurf.ai/docs/cli)

No API key required to start — you get 30 free credits daily. For full access, sign up at [agents.asksurf.ai](https://agents.asksurf.ai) and run:

```bash
surf auth --api-key $API_KEY
```

## What It Does

Once installed, your agent can fetch live crypto data just by you asking for it — no endpoints to memorize.

**Example prompts your agent will handle:**

- "What's the price of ETH?"
- "Show me the top 10 wallets holding AAVE"
- "Get Polymarket odds for the next US election"
- "Find trending crypto projects on Twitter"
- "What's the TVL of Uniswap on Arbitrum?"
- "Show me BTC funding rates across exchanges"

The skill teaches the agent to discover endpoints, use correct parameters, and return structured data — automatically.

## Data Coverage

| Domain | What You Can Query |
|--------|-------------------|
| **Market** | Prices, rankings, technical indicators (RSI, MACD, Bollinger), fear & greed, liquidations, futures, options, ETFs |
| **Exchange** | Order books, candlesticks, funding rates, long/short ratios, perpetual contracts |
| **Matching** | CEX-DEX matching, market matching |
| **Wallet** | Balances, transfers, DeFi positions, net worth, wallet labels |
| **Social** | Twitter/X profiles, posts, followers, mindshare, sentiment, smart followers |
| **Token** | Holders, DEX trades, transfers, unlock schedules, tokenomics |
| **Project** | Profiles, DeFi TVL, protocol metrics, DeFi rankings |
| **Prediction Markets** | Polymarket & Kalshi — markets, trades, prices, volume, open interest, rankings |
| **On-chain** | Transaction lookup, SQL queries, gas prices, bridge rankings, yield rankings |
| **News & Search** | Cross-domain entity search, news feed, web fetch |
| **Fund** | VC fund profiles, portfolios, rankings |

## CLI Quick Reference

The skill uses the `surf` CLI under the hood. You can also use it directly:

```bash
# Discovery
surf sync                                    # Refresh API spec cache
surf list-operations                         # All available commands
surf list-operations | grep market           # Filter by domain
surf market-price --help                     # Full params and enums

# Fetch data
surf market-price --symbol BTC -o json -f body.data
surf wallet-detail --address 0x... -o json -f body.data
surf social-user --handle vitalikbuterin -o json -f body.data

# On-chain SQL
echo '{"sql":"SELECT project, sum(amount_usd) FROM agent.ethereum_dex_trades WHERE block_date = today() - 1 GROUP BY project ORDER BY 2 DESC LIMIT 10"}' | surf onchain-sql
```

## Documentation

| Resource | Link |
|----------|------|
| **Full Docs** | [docs.asksurf.ai](https://docs.asksurf.ai) |
| **CLI & Skills Guide** | [docs.asksurf.ai/cli/introduction](https://docs.asksurf.ai/cli/introduction) |
| **Data API (83 endpoints)** | [docs.asksurf.ai/data-api/overview](https://docs.asksurf.ai/data-api/overview) |
| **Onchain SQL (58 tables)** | [docs.asksurf.ai/data-catalog/overview](https://docs.asksurf.ai/data-catalog/overview) |

## How It Works

The skill (`skills/surf/SKILL.md`) is an instruction file that teaches your AI agent to:

1. Run `surf sync` to refresh the API spec cache
2. Use `surf list-operations` and `surf <command> --help` to discover the right endpoint
3. Use `-o json -f body.data` for structured output
4. Map natural language requests to the correct domain and parameters
5. Handle pagination, chain name conventions, and common gotchas

No code generation needed — the agent calls the CLI directly and returns the data.

## Adding New Endpoints

No changes needed in this repo. When a new API endpoint is added upstream:

1. The OpenAPI spec updates automatically
2. `surf list-operations` shows the new command
3. `surf <new-command> --help` shows its parameters
