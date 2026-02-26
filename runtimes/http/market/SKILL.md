---
name: market
description: >
  Query market data: spot prices, futures, options, liquidations,
  technical indicators, on-chain market indicators, ETF flows, trading volume,
  trending coins, and predictions.
  Keywords: price, futures, options, liquidation, RSI, MACD, SOPR, NUPL, ETF, volume, funding rate, OI, trending, TGE.
---

# Market Data

## API Access

All endpoints: `${{BASE_URL_VAR}}/market/{endpoint}`

{{AUTH_NOTE}}

## Quick Examples

```bash
curl -s "${{BASE_URL_VAR}}/market/price?ids=bitcoin&vs_currencies=usd"
curl -s "${{BASE_URL_VAR}}/market/futures?symbol=BTC"
curl -s "${{BASE_URL_VAR}}/market/indicator?name=rsi&symbol=BTC/USDT&interval=1d&exchange=binance"
curl -s "${{BASE_URL_VAR}}/market/market-indicator?asset=btc&metric=sopr&window=day&limit=30"
curl -s "${{BASE_URL_VAR}}/market/etf?type=us-btc-spot"
curl -s "${{BASE_URL_VAR}}/market/trending"
curl -s "${{BASE_URL_VAR}}/market/search?query=solana"
```

## When NOT to Use

- Protocol metrics (revenue, TVL, fees) -> `project-data`
- Wallet/address analysis -> `wallet-data`
- Raw on-chain SQL -> `onchain-sql`
- Token holders -> `token-data`

## Knowledge
