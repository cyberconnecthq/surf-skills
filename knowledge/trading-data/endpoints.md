# Trading Data — Endpoint Reference

<!-- TODO: endpoints will be restructured after hermod refactor -->

## Semantic Endpoints (1 credit)

| Endpoint | Provider | Key Params |
|----------|----------|------------|
| `GET /price` | CoinGecko | `ids`, `vs_currencies` |
| `GET /future` | CoinGlass | `symbol` |
| `GET /option` | CoinGlass | `symbol` |
| `GET /liquidation` | CoinGlass | `symbol` |
| `GET /indicator` | TAAPI | `name`, `symbol` (PAIR/QUOTE), `interval`, `exchange` |
| `GET /market-indicator` | CryptoQuant | `asset`, `metric`, `window`, `limit` |
| `GET /etf` | SoSoValue | `type` (us-btc-spot, us-eth-spot) |
| `GET /volume` | CoinGlass | `symbol` |

## Proxy Endpoints (2-3 credits)

Direct upstream API calls via `/proxy/{service}/...` with auto API key injection.

| Service | Credit | Examples |
|---------|--------|----------|
| coingecko | 2 | markets, ohlc, trending, search, categories, companies |
| coinglass | 3 | coins-markets (all-in-one), ahr999, OI chart, funding rate |
| taapi | 2 | 200+ indicators via `/proxy/taapi/indicator/{name}` |
| cryptoquant | 3 | exchange-flows, sopr, nupl, miner-revenue |
| sosovalue | 2 | ETF flows by date |

See `responses.md` for verified response JSON and field documentation.
