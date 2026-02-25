---
name: surf-trading-data
description: Query crypto trading data including prices, futures, options, liquidations, and market indicators
tools: ["bash"]
---

# Trading Data — Crypto Market Data

Access real-time and historical crypto trading data via the Hermod API Gateway. Covers prices, futures, options, liquidations, technical indicators, ETFs, and volume.

## When to Use

Use this skill when you need to:
- Get current or historical crypto prices
- Check futures and options market data
- Monitor liquidation events
- Calculate technical indicators (RSI, MACD, etc.)
- Track ETF flow data
- Analyze market-wide indicators and volume

## CLI Usage

```bash
# Check setup
surf-trading-data/scripts/surf-trading --check-setup

# Get price data (CoinGecko — use coingecko id, not ticker)
surf-trading-data/scripts/surf-trading price --ids bitcoin,ethereum --vs usd

# Get futures data (CoinGlass)
surf-trading-data/scripts/surf-trading future --symbol BTC

# Get options data (CoinGlass)
surf-trading-data/scripts/surf-trading option --symbol BTC

# Get liquidation data (CoinGlass)
surf-trading-data/scripts/surf-trading liquidation --symbol BTC

# Get technical indicator (TAAPI — symbol in PAIR/QUOTE format)
surf-trading-data/scripts/surf-trading indicator --name rsi --symbol BTC/USDT --interval 1d --exchange binance

# Get market-wide indicator (CryptoQuant)
surf-trading-data/scripts/surf-trading market-indicator --asset btc --metric market-indicator/sopr --window day --limit 5

# Get ETF data (SoSoValue)
surf-trading-data/scripts/surf-trading etf --type us-btc-spot

# Get volume data (CoinGlass)
surf-trading-data/scripts/surf-trading volume --symbol BTC
```

## Cost

1 credit per request.

## Endpoints Reference

See `references/endpoints.md` for full parameter details and response formats.
