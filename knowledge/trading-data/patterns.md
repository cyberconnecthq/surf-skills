# Trading Data — Patterns & Gotchas

<!-- TODO: will be updated after hermod refactor -->

## Common Gotchas

1. **CoinGlass `code` is string `"0"`**, not integer — use `==` not `===`
2. **CryptoQuant** response field matches metric name (`sopr`, `mvrv`), not generic `value`
3. **SoSoValue** values are strings — must `parseFloat()` / `float()`
4. **CoinGecko `/price`** uses coin IDs (`bitcoin`), not tickers (`BTC`)
5. **TAAPI `/indicator`** uses pair format (`BTC/USDT`), not coin IDs

## When to Use What

| Need | Use |
|------|-----|
| Current price | `/price` (1 credit) |
| Futures all-in-one (funding+OI+price) | proxy `coinglass/coins-markets` (3 credits) |
| Technical analysis | `/indicator` |
| Macro sentiment | `/market-indicator` (SOPR, MVRV, netflow) |
| OHLCV candles | proxy `coingecko/coins/{id}/ohlc` |
| Find CoinGecko ID | proxy `coingecko/search` |

## Skill Boundaries

- Protocol metrics (revenue, TVL) → `project-data`
- Wallet/address → `wallet-data`
- On-chain SQL → `raw-onchain` / `onchain-sql`
- Token holders → `token-data`
