---
name: surf-market
description: Check crypto prices, run technical analysis, monitor derivatives and ETF flows, and track market trends
tools: ["bash"]
---

# Market Data — Prices, Indicators, Derivatives & Trends

Real-time crypto market data: spot prices, 14 technical indicators, futures/options derivatives, ETF flows, on-chain metrics, liquidations, and market rankings.

## Quick Reference

| Command | Description | Cost |
|---------|-------------|------|
| `price` | Spot prices for any crypto assets | 1 credit |
| `price-metrics` | Price time-series (charts) over N days | 1 credit |
| `indicator` | Technical indicators (RSI, MACD, EMA, BBands, etc.) | 1 credit |
| `top` | Market rankings: market_cap, gainers, losers, fear/greed, funding, OI, liquidations | 1 credit |
| `futures` | Futures OI, funding rates, long/short ratios | 1 credit |
| `options` | Options OI by exchange | 1 credit |
| `liquidation` | Liquidation data (1h/4h/12h/24h, long vs short) | 1 credit |
| `volume` | Trading volume by exchange | 1 credit |
| `etf` | BTC/ETH spot ETF flows, AUM, holdings | 1 credit |
| `market-indicator` | On-chain metrics: NUPL, SOPR, MVRV, exchange flows | 1 credit |
| `trending` | Trending coins (general, DEX, mindshare, smart money) | 1 credit |
| `search` | Search for any crypto asset by name | 1 credit |
| `tge` | Upcoming Token Generation Events | 1 credit |
| `prediction` | Prediction market data (by market_id query param) | 1 credit |
| `prediction-detail` | Prediction market detail (by --id or --q entity) | 1 credit |

## Common Tasks

### Task: Check current market conditions
Get a quick snapshot of prices and market sentiment.
```bash
# Get BTC and ETH prices
surf-market price --ids bitcoin,ethereum,solana --vs-currencies usd

# Check Fear & Greed Index
surf-market top --metric fear_greed

# See top gainers and losers
surf-market top --metric top_gainers
surf-market top --metric top_losers

# Market overview (market cap, volume, BTC dominance)
surf-market top --metric market_overview
```
**What to look for:** Fear & Greed below 25 = Extreme Fear (potential buying opportunity). Above 75 = Extreme Greed (potential top). Compare 24h price changes across assets to gauge rotation.

### Task: Run technical analysis on a trading pair
Evaluate entry/exit signals using technical indicators.
```bash
# RSI — overbought (>70) or oversold (<30)
surf-market indicator --name rsi --symbol BTC/USDT

# MACD — trend direction and momentum
surf-market indicator --name macd --symbol BTC/USDT

# Bollinger Bands — volatility and mean reversion
surf-market indicator --name bbands --symbol ETH/USDT

# EMA — trend following (use with different intervals)
surf-market indicator --name ema --symbol SOL/USDT --interval 4h

# Supertrend — trend direction with stop levels
surf-market indicator --name supertrend --symbol BTC/USDT --interval 1d

# Ichimoku Cloud — comprehensive trend analysis
surf-market indicator --name ichimoku --symbol BTC/USDT --interval 1d
```
**Available indicators:** rsi, macd, ema, sma, bbands, stoch, adx, atr, cci, obv, vwap, dmi, ichimoku, supertrend

**What to look for:** RSI divergences from price, MACD crossovers, price touching Bollinger Band edges. Combine multiple indicators for confirmation. Default interval is 1d; use `--interval 4h` or `--interval 1h` for shorter timeframes.

### Task: Monitor derivatives markets
Assess leverage, positioning, and liquidation risk.
```bash
# Futures overview — OI, funding, long/short ratios
surf-market futures --symbol BTC

# Liquidation data — who's getting rekt
surf-market liquidation --symbol BTC

# Options open interest by exchange
surf-market options --symbol BTC

# Funding rates across all assets
surf-market top --metric funding_rate

# Open interest rankings
surf-market top --metric open_interest

# Long/short ratio rankings
surf-market top --metric long_short_ratio

# Liquidation rankings
surf-market top --metric liquidations
```
**What to look for:** Extreme funding rates (>0.05% = overleveraged longs, <-0.02% = overleveraged shorts). Long/short ratio far from 1.0 signals crowded positioning. Large 24h liquidations indicate forced selling/buying.

### Task: Track ETF flows
Monitor institutional money flows through spot Bitcoin and Ethereum ETFs.
```bash
# BTC spot ETF flows and holdings
surf-market etf --type us-btc-spot

# ETH spot ETF flows and holdings
surf-market etf --type us-eth-spot
```
**Available types:** us-btc-spot, us-eth-spot

**What to look for:** Daily net inflow/outflow signals institutional sentiment. Compare individual ETF flows (IBIT, FBTC, GBTC). Cumulative net inflow trend shows sustained institutional demand. Total token holdings indicate how much supply is locked in ETFs.

### Task: Analyze on-chain market cycles
Use on-chain metrics to assess market cycle positioning.
```bash
# NUPL (Net Unrealized Profit/Loss) — market cycle phase
surf-market market-indicator --asset btc --metric nupl --window day --limit 30

# SOPR (Spent Output Profit Ratio) — profit-taking behavior
surf-market market-indicator --asset btc --metric sopr --window day --limit 30

# MVRV — market value vs realized value
surf-market market-indicator --asset btc --metric mvrv --window day --limit 30

# Exchange inflows — selling pressure
surf-market market-indicator --asset btc --metric exchange-flows/inflow --window day --limit 20

# Exchange outflows — accumulation
surf-market market-indicator --asset btc --metric exchange-flows/outflow --window day --limit 20

# Exchange net flows — net buy/sell pressure
surf-market market-indicator --asset btc --metric exchange-flows/netflow --window day --limit 20
```
**Available metrics:** nupl, sopr, mvrv, puell-multiple, nvm, nvt, nvt-golden-cross, rhodl-ratio, exchange-flows/inflow, exchange-flows/outflow, exchange-flows/netflow

**What to look for:** NUPL > 0.75 = euphoria (cycle top zone). SOPR > 1 = holders selling at profit. MVRV > 3.5 = historically overvalued. Negative exchange netflow = coins leaving exchanges (bullish accumulation).

### Task: Find trending coins and narratives
Discover what's gaining attention and smart money interest.
```bash
# General trending coins (fixed limit of 10, --limit not supported)
surf-market trending --type general

# Trending on DEXes (early signals)
surf-market trending --type dex

# Mindshare trending (social attention)
surf-market trending --type mindshare

# Smart money following
surf-market trending --type smart_following
```
**Available types:** general, dex, mindshare, smart_following

**What to look for:** Coins trending on DEX before CEX can signal early momentum. Smart following trends show what sophisticated traders are watching. Cross-reference trending coins with their fundamentals before acting.

### Task: Research a specific asset's price history
Get historical price data for charting or analysis.
```bash
# BTC 30-day price history
surf-market price-metrics --id bitcoin --days 30 --vs-currency usd

# ETH 7-day price history
surf-market price-metrics --id ethereum --days 7 --vs-currency usd

# Search for an asset by name to get its ID
surf-market search --query solana
```
**What to look for:** Use price-metrics data to calculate support/resistance levels, identify trends, or compare asset performance over matching time periods.

### Task: Monitor upcoming token launches
Track Token Generation Events (TGEs) for new investment opportunities.
```bash
# Upcoming TGEs
surf-market tge --status upcoming

# Pre-TGE projects (already announced)
surf-market tge --status pre

# Post-TGE projects (recently launched)
surf-market tge --status post
```
**Available statuses:** upcoming, pre, post

## Cross-Domain Workflows

### Full Market Report
Combine market data with news and web research for comprehensive analysis.
```bash
# 1. Price + sentiment snapshot
surf-market price --ids bitcoin,ethereum,solana --vs-currencies usd
surf-market top --metric fear_greed

# 2. Technical picture
surf-market indicator --name rsi --symbol BTC/USDT
surf-market indicator --name macd --symbol BTC/USDT

# 3. Derivatives positioning
surf-market futures --symbol BTC
surf-market liquidation --symbol BTC

# 4. Institutional flows
surf-market etf --type us-btc-spot

# 5. On-chain health
surf-market market-indicator --asset btc --metric nupl --window day --limit 7

# 6. News context (use surf-news)
surf-news search --query "bitcoin market" --limit 5
```

## Tips
- All output is JSON. Data goes to stdout, errors to stderr.
- Use `--limit` on list endpoints to control response size and save context window.
- Default interval for indicators is `1d`. Override with `--interval 1h`, `--interval 4h`, etc.
- Combine `top --metric` rankings with asset-specific `futures` or `indicator` queries for deep dives.
- Price IDs use slug format (bitcoin, ethereum, solana). Trading pairs use symbol format (BTC/USDT, ETH/USDT).
- Run `--check-setup` to verify your API credentials before first use.
