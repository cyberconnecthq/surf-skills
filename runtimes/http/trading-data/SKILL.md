---
name: trading-data
description: >
  Query trading and market data: spot prices, futures, options, liquidations,
  technical indicators, on-chain market indicators, ETF flows, and trading volume.
  Keywords: price, futures, options, liquidation, RSI, MACD, SOPR, NUPL, ETF, volume, funding rate, OI.
---

# Trading Data

## API Access

All endpoints: `${{BASE_URL_VAR}}/trading-data/{endpoint}`

{{AUTH_NOTE}}

## Quick Examples

```bash
curl -s "${{BASE_URL_VAR}}/trading-data/price?ids=bitcoin&vs_currencies=usd"
curl -s "${{BASE_URL_VAR}}/trading-data/future?symbol=BTC"
curl -s "${{BASE_URL_VAR}}/trading-data/indicator?name=rsi&symbol=BTC/USDT&interval=1d&exchange=binance"
curl -s "${{BASE_URL_VAR}}/trading-data/market-indicator?asset=btc&metric=sopr&window=day&limit=30"
curl -s "${{BASE_URL_VAR}}/trading-data/etf?type=us-btc-spot"
```

## When NOT to Use

- Protocol metrics (revenue, TVL, fees) → `project-data`
- Wallet/address analysis → `wallet-data`
- Raw on-chain SQL → `raw-onchain`
- Token holders → `token-data`

## Knowledge
