---
name: surf-trading-data
description: Query crypto trading data including prices, futures, options, liquidations, and market indicators
tools: ["bash"]
---

# Trading Data — Crypto Market Data

Access real-time and historical crypto trading data via the Hermod API Gateway. Covers prices, futures, options, liquidations, technical indicators, ETFs, volume, market cap rankings, and top movers.

## When to Use

Use this skill when you need to:
- Get current or historical crypto prices
- Check futures funding rates and OI/market cap ratios
- Check futures and options market data
- Monitor liquidation events
- Calculate technical indicators (RSI, MACD, etc.)
- Track ETF flow data
- Analyze market-wide indicators and volume
- View market cap rankings and top gainers/losers
- Search for a coin's CoinGecko ID (needed for price lookups)
- Get detailed coin info (ATH, supply, market cap breakdown)

## CLI Usage

```bash
# Check setup
surf-trading-data/scripts/surf-trading --check-setup

# Get price data (CoinGecko — use coingecko id, not ticker)
surf-trading-data/scripts/surf-trading price --ids bitcoin,ethereum --vs usd

# Get funding rates + OI/MCap ratios for top coins (CoinGlass — RECOMMENDED for market overview)
surf-trading-data/scripts/surf-trading cg-markets --limit 10
surf-trading-data/scripts/surf-trading cg-markets --symbol BTC

# Get futures data (CoinGlass — WARNING: large response, always use --limit)
surf-trading-data/scripts/surf-trading future --symbol BTC --limit 5

# Get options data (CoinGlass)
surf-trading-data/scripts/surf-trading option --symbol BTC --limit 5

# Get liquidation data (CoinGlass)
surf-trading-data/scripts/surf-trading liquidation --symbol BTC --limit 5

# Get technical indicator (TAAPI — symbol in PAIR/QUOTE format)
surf-trading-data/scripts/surf-trading indicator --name rsi --symbol BTC/USDT --interval 1d --exchange binance

# Get market-wide indicator (CryptoQuant)
surf-trading-data/scripts/surf-trading market-indicator --asset btc --metric market-indicator/sopr --window day --limit 5

# Get ETF data (SoSoValue — types: us-btc-spot, us-eth-spot)
surf-trading-data/scripts/surf-trading etf --type us-btc-spot

# Get volume data (CoinGlass)
surf-trading-data/scripts/surf-trading volume --symbol BTC --limit 5

# Market cap ranking with 24h change (CoinGecko proxy, 2 credits)
surf-trading-data/scripts/surf-trading cg-market-cap --limit 20

# Top gainers and losers in 24h (CoinGecko proxy, 2 credits)
surf-trading-data/scripts/surf-trading cg-movers

# Search coins by name — find CoinGecko ID for price lookups (2 credits)
surf-trading-data/scripts/surf-trading cg-search --query solana

# Full coin detail: ATH, supply, market cap (CoinGecko proxy, 2 credits)
surf-trading-data/scripts/surf-trading cg-coin --id bitcoin
```

## Important Notes

- **Use `--limit` on `future`, `option`, `liquidation`, `volume`** — these return large JSON without it
- **Use `cg-markets` for funding rate analysis** — returns price, funding rate, OI ratio in one call
- **Use `cg-search` to find CoinGecko ID** — `price` command needs CoinGecko ID (e.g. `bitcoin`), not ticker (e.g. `BTC`)
- **ETF types**: `us-btc-spot`, `us-eth-spot`

## Cost

- Semantic endpoints (price, future, indicator, etc.): 1 credit
- CoinGlass proxy (cg-markets): 3 credits
- CoinGecko proxy (cg-*): 2 credits

## Endpoints Reference

See `references/endpoints.md` for full parameter details and response formats.
