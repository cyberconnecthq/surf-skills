# Market Data — Endpoint Reference

<!-- Hermod /v1/market/* — endpoint inventory will evolve as hermod stabilizes -->

## Endpoints

All endpoints are under `/v1/market/`.

| Endpoint | Description | Key Params |
|----------|-------------|------------|
| `GET /price` | Spot prices | `ids`, `vs_currencies` |
| `GET /price/:id/metrics` | Price metrics for a specific coin | `:id` (path) |
| `GET /futures` | Futures open interest | `symbol` |
| `GET /options` | Options data | `symbol` |
| `GET /liquidation` | Liquidation data | `symbol` |
| `GET /volume` | Trading volume | `symbol` |
| `GET /etf` | ETF flows | `type` (us-btc-spot, us-eth-spot) |
| `GET /indicator` | Technical indicators (RSI, MACD, etc.) | `name`, `symbol` (PAIR/QUOTE), `interval`, `exchange` |
| `GET /market-indicator` | On-chain market indicators | `asset`, `metric`, `window`, `limit` |
| `GET /search` | Search coins/tokens | `query` |
| `GET /top` | Top coins by market cap | `limit` |
| `GET /trending` | Trending coins | — |
| `GET /tge` | Token generation events | — |
| `GET /prediction/:market_id` | Prediction market data | `:market_id` (path) |
| `GET /prediction/detail` | Prediction market detail | TODO: params TBD |

<!-- TODO: Exact params and response shapes will be documented as hermod endpoints are finalized -->

## Notes

- All endpoints return 1 credit cost unless otherwise documented
- Hermod handles all upstream provider routing internally — no direct third-party API paths
- Some endpoints may still return `model.RawJSON` (will be typed later)
