# Market Data — Endpoint Reference

<!-- Hermod /v1/market/* — standardized market data endpoints -->

## Endpoints

All endpoints are under `/v1/market/`. Response envelope: `{"data": [...], "meta": {...}}`.

| Endpoint | Description | Key Params | Cost |
|----------|-------------|------------|------|
| `GET /etf` | Get ETF metrics | `type` (required) | 1 credit |
| `GET /futures` | Get futures market data | `symbol` | 1 credit |
| `GET /indicator` | Get technical indicator | `name` (required), `symbol` (required), `interval`, `exchange` | 1 credit |
| `GET /liquidation` | Get liquidation data | `symbol` | 1 credit |
| `GET /market-indicator` | Get on-chain market metrics | `asset` (required), `metric` (required), `window`, `limit`, `exchange` | 1 credit |
| `GET /options` | Get options market data | `symbol` (required) | 1 credit |
| `GET /prediction/{market_id}` | Get prediction market data | `market_id` (required) | 1 credit |
| `GET /prediction/detail` | Get prediction market detail for a project | `project_id` (required) | 1 credit |
| `GET /price` | Get price data for crypto assets | `ids` (required), `vs_currencies`, `include_24hr_change`, `include_market_cap` | 1 credit |
| `GET /price/{id}/metrics` | Get price time-series metrics | `id` (required), `days`, `vs_currency` | 1 credit |
| `GET /search` | Search market assets | `q` (required) | 1 credit |
| `GET /tge` | Get TGE (Token Generation Event) projects | `status` | 1 credit |
| `GET /top` | Get top/ranked market data | `metric` (required) | 1 credit |
| `GET /trending` | Get trending data | `type` (required), `limit`, `offset` | 1 credit |
| `GET /volume` | Get trading volume data | `symbol` | 1 credit |

### etf — Valid Parameter Values

**`type`**: `us-btc-spot`, `us-eth-spot`

### indicator — Valid Parameter Values

**`name`**: `rsi`, `macd`, `ema`, `sma`, `bbands`, `stoch`, `adx`, `atr`, `cci`, `obv`, `vwap`, `dmi`, `ichimoku`, `supertrend`

**`interval`**: `1m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `12h`, `1d`, `1w`

**`exchange`**: `binance`, `bybit`, `coinbase`, `kraken`

### market-indicator — Valid Parameter Values

**`metric`**: `nupl`, `sopr`, `mvrv`, `puell-multiple`, `nvm`, `nvt`, `nvt-golden-cross`, `rhodl-ratio`, `exchange-flows/inflow`, `exchange-flows/outflow`, `exchange-flows/netflow`

**`window`**: `day`, `block`

### price — Valid Parameter Values

**`include_24hr_change`**: `true`, `false`

**`include_market_cap`**: `true`, `false`

### price-metrics — Valid Parameter Values

**`days`**: `1`, `7`, `14`, `30`, `90`, `180`, `365`, `max`

### tge — Valid Parameter Values

**`status`**: `upcoming`, `pre`, `post`

### top — Valid Parameter Values

**`metric`**: `top_gainers`, `top_losers`, `market_overview`, `fear_greed`, `funding_rate`, `open_interest`, `liquidations`, `long_short_ratio`

### trending — Valid Parameter Values

**`type`**: `general`, `dex`, `mindshare`, `smart_following`

