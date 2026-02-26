# Market Data — Patterns & Gotchas

## Common Gotchas

1. **CoinGecko `/price`** uses coin IDs (`bitcoin`), not tickers (`BTC`)
2. **TAAPI `/indicator`** uses pair format (`BTC/USDT`), not coin IDs
3. **Market indicator** response field matches metric name (`sopr`, `mvrv`), not a generic `value`
4. **Futures/options endpoints** can return large arrays — always use `limit` param when available

## When to Use What

| Need | Endpoint |
|------|----------|
| Current price | `/market/price` |
| Technical analysis | `/market/indicator` |
| Macro sentiment (SOPR, MVRV, netflow) | `/market/market-indicator` |
| Futures data (OI, funding) | `/market/futures` |
| ETF flows | `/market/etf` |
| Trending coins | `/market/trending` |
| Find a coin | `/market/search` |
| Top coins by market cap | `/market/top` |

## Skill Boundaries

- Protocol metrics (revenue, TVL) -> `project-data`
- Wallet/address -> `wallet-data`
- On-chain SQL -> `onchain-sql`
- Token holders -> `token-data`
- News -> `news-data`
- Social/X data -> `x-data`
