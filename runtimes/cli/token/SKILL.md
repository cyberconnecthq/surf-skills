---
name: surf-token
description: Analyze token fundamentals, monitor capital flows (exchange + ETF), find trending tokens, and check unlock schedules
tools: ["bash"]
---

# Token Data — On-chain Token Analytics

Query token metadata, holder distributions, capital flow metrics (exchange flows, reserves, ETF), rankings, transfers, and unlock schedules. All data via Hermod API Gateway.

## Quick Reference

| Command | Description | Key Params | Cost |
|---------|-------------|------------|------|
| `search` | Find tokens by name/symbol | `--query` | 1 |
| `info` | Token metadata (supply, links, chains) | `--address`, `--chain` | 1 |
| `holders` | Top holder addresses + percentages | `--address`, `--chain`, `--limit` | 1 |
| `top` | Ranked tokens by metric | `--metric`, `--limit` | 1 |
| `metrics` | Time-series: exchange flow, reserve, ETF | `--asset`, `--metric`, `--window`, `--limit` | 1 |
| `transfers` | Recent token transfers | `--address`, `--chain`, `--limit` | 1 |
| `top-traders` | Top traders for a token | `--address` | 1 |
| `unlock` | Token unlock schedule | `--id`, `--timeframe` | 1 |

## Common Tasks

### Task: Analyze Token Fundamentals

Look up a token's metadata, holder concentration, and top traders.

```bash
# Step 1: Find the token
runtimes/cli/token/scripts/surf-token search --query ethereum

# Step 2: Get full metadata (supply, links, categories, multi-chain deployments)
runtimes/cli/token/scripts/surf-token info --address 0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48 --chain eth

# Step 3: Check holder concentration — top 10 holders
runtimes/cli/token/scripts/surf-token holders --address 0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48 --chain eth --limit 10

# Step 4: See who is actively trading it
runtimes/cli/token/scripts/surf-token top-traders --address 0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48
```

**What to look for:** High holder concentration (top 10 > 50%) signals centralization risk. Check if top holders are contracts (exchanges, DeFi protocols) vs. EOAs. Compare `circulating_supply` vs `total_supply` for dilution risk.

### Task: Monitor Capital Flows (Exchange Flow + Exchange Reserve)

Track BTC/ETH moving in and out of exchanges — a key indicator of sell pressure vs. accumulation.

```bash
# Step 1: Net exchange flow (positive = inflow/sell pressure, negative = outflow/accumulation)
runtimes/cli/token/scripts/surf-token metrics --asset btc --metric exchange_flow --window day --limit 7

# Step 2: Total exchange reserves over time
runtimes/cli/token/scripts/surf-token metrics --asset btc --metric exchange_reserve --window day --limit 7

# Step 3: Compare ETH flows
runtimes/cli/token/scripts/surf-token metrics --asset eth --metric exchange_flow --window day --limit 7
```

**What to look for:** Sustained negative exchange flow = accumulation (bullish). Rising exchange reserves = potential sell pressure. Compare BTC vs ETH flows to gauge market-wide sentiment vs. asset-specific trends.

### Task: Track ETF Capital Flows

Monitor daily BTC/ETH spot ETF inflows and outflows.

```bash
# BTC spot ETF daily flows (totalNetInflow, totalNetAssets, cumNetInflow)
runtimes/cli/token/scripts/surf-token metrics --asset btc --metric etf_flow --type us-btc-spot --limit 7

# ETH spot ETF daily flows
runtimes/cli/token/scripts/surf-token metrics --asset eth --metric etf_flow --type us-eth-spot --limit 7
```

**What to look for:** `totalNetInflow` positive = new money entering. Track `cumNetInflow` trend for sustained demand. Compare BTC vs ETH ETF flows to spot rotation between assets. Large single-day outflows may signal institutional repositioning.

### Task: Find Hot Tokens (Trending & Movers)

Discover which tokens are trending by volume, price movement, or exchange activity.

```bash
# Top tokens by 24h trading volume
runtimes/cli/token/scripts/surf-token top --metric volume --limit 10

# Biggest gainers today
runtimes/cli/token/scripts/surf-token top --metric gainers --limit 10

# Biggest losers today
runtimes/cli/token/scripts/surf-token top --metric losers --limit 10

# Tokens with highest exchange inflows (potential sell pressure)
runtimes/cli/token/scripts/surf-token top --metric exchange_inflow --limit 10

# Tokens with highest exchange outflows (accumulation signals)
runtimes/cli/token/scripts/surf-token top --metric exchange_outflow --limit 10

# Top tokens by social mindshare
runtimes/cli/token/scripts/surf-token top --metric mindshare --limit 10
```

**What to look for:** Volume spikes without price movement may precede breakouts. Cross-reference gainers with exchange_inflow to see if rallies are being sold into. High mindshare + low volume = speculative interest not yet priced in.

### Task: Token Unlock Analysis

Check upcoming token unlocks that could create sell pressure.

```bash
# Get unlock schedule for a project
runtimes/cli/token/scripts/surf-token unlock --id arbitrum

# Check with specific timeframe
runtimes/cli/token/scripts/surf-token unlock --id optimism --timeframe 30d
```

**What to look for:** Large unlocks (>2% of circulating supply) often create sell pressure. Check who receives the unlock (team, investors, ecosystem). Compare unlock size to average daily volume — if unlock > 5x daily volume, expect significant impact.

### Task: Full Token Report (Cross-Domain)

Combine token data with market and project data for comprehensive analysis.

```bash
# 1. Token fundamentals
runtimes/cli/token/scripts/surf-token info --address 0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48 --chain eth
runtimes/cli/token/scripts/surf-token holders --address 0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48 --chain eth --limit 10

# 2. Market context (use surf-market)
runtimes/cli/market/scripts/surf-market price --ids usd-coin --vs usd
runtimes/cli/market/scripts/surf-market chart --id usd-coin --vs usd --days 30

# 3. Project fundamentals (use surf-project)
runtimes/cli/project/scripts/surf-project overview --id usd-coin

# 4. Recent news (use surf-news)
runtimes/cli/news/scripts/surf-news search --query "USDC"

# 5. Social sentiment (use surf-social)
runtimes/cli/social/scripts/surf-social search --query "USDC" --limit 5
```

## Cross-Domain Workflows

- **Token + Market**: Combine `info` (supply data) with `surf-market price` (current price) to calculate real-time market cap. Use `surf-market chart` for price history alongside `metrics exchange_flow` for flow-price correlation.
- **Token + Project**: Use `surf-project overview` for TVL/revenue alongside `holders` to understand protocol health. A token with growing TVL but concentrated holders may have governance risks.
- **Token + Social**: Cross-reference `top --metric mindshare` with `surf-social search` to validate whether social buzz is organic or bot-driven.
- **Token + Wallet**: Use `holders` to find top addresses, then investigate them with `surf-wallet tokens` and `surf-wallet labels` to identify if whales are accumulating.

## Valid Parameter Values

| Parameter | Valid Values |
|-----------|-------------|
| `--chain` (holders, info) | `eth`, `bsc`, `polygon`, `avalanche`, `fantom`, `arbitrum`, `optimism`, `solana` |
| `--chain` (transfers) | `eth`, `solana` |
| `--metric` (metrics) | `exchange_flow`, `etf_flow`, `exchange_reserve` |
| `--metric` (top) | `volume`, `gainers`, `losers`, `exchange_inflow`, `exchange_outflow`, `mindshare` |
| `--window` (metrics) | `day`, `hour` |
| `--type` (etf_flow) | `us-btc-spot`, `us-eth-spot` |
| `--sort` (transfers) | `asc`, `desc` |

## Tips

- Use `--limit` on all list commands to control response size and save context window space.
- `search` returns CoinGecko IDs (e.g., `ethereum`, `usd-coin`) — use these for `unlock --id` and cross-referencing with `surf-market` and `surf-project`.
- `info` returns multi-chain deployment addresses in `implementations` — use these to query holders/transfers on other chains.
- `metrics` uses asset symbols (`btc`, `eth`) not CoinGecko IDs — lowercase ticker symbols.
- `holders` returns raw token amounts (not USD) — divide by `10^decimals` from `info` to get human-readable values.
- `exchange_flow` values: positive = net inflow to exchanges (bearish), negative = net outflow (bullish).
- All output is JSON. Data to stdout, errors to stderr.
