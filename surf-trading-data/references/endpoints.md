# Trading Data — Endpoint Reference

## Semantic Endpoints

Base path: `/gateway/v1/trading-data`. Cost: 1 credit each.

Each endpoint proxies to a specific upstream provider. Parameter names match the upstream API.

### GET /price (upstream: CoinGecko)
Get price data. Params: `ids` (required, coingecko id e.g. bitcoin,ethereum), `vs_currencies` (optional, default usd), `include_24hr_change` (optional, true/false).

### GET /future (upstream: CoinGlass)
Get futures open interest data. Params: `symbol` (required, e.g. BTC, ETH).

### GET /option (upstream: CoinGlass)
Get options data. Params: `symbol` (required).

### GET /liquidation (upstream: CoinGlass)
Get liquidation data. Params: `symbol` (required).

### GET /indicator (upstream: TAAPI)
Get technical indicator. Params: `name` (required: rsi, macd, ema, sma, bbands), `symbol` (required, PAIR/QUOTE format e.g. BTC/USDT), `interval` (optional: 1m, 5m, 15m, 1h, 4h, 1d, 1w), `exchange` (optional, default binance).

### GET /market-indicator (upstream: CryptoQuant)
Get market-wide on-chain metric. Params: `asset` (required: btc, eth), `metric` (required, e.g. market-indicator/sopr, market-indicator/nupl), `window` (optional: day, hour), `limit` (optional).

### GET /etf (upstream: SoSoValue)
Get ETF flow data. Params: `type` (required: us-btc-spot, us-eth-spot).

### GET /volume (upstream: CoinGlass)
Get volume data. Params: `symbol` (required).

---

## Proxy Endpoints (Advanced)

For more granular data, use the proxy routes at `/gateway/v1/proxy/{service}/...`. These call upstream APIs directly through Hermod with automatic API key injection.

### CoinGecko — Price & Market Data (2 credits)

```bash
# Simple price lookup (multi-token)
GET /gateway/v1/proxy/coingecko/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true

# OHLCV candles
GET /gateway/v1/proxy/coingecko/api/v3/coins/bitcoin/ohlc?vs_currency=usd&days=30

# Trending tokens
GET /gateway/v1/proxy/coingecko/api/v3/search/trending

# Global market data
GET /gateway/v1/proxy/coingecko/api/v3/global
```

### CoinGlass — Derivatives & Futures (3 credits)

```bash
# Open Interest
GET /gateway/v1/proxy/coinglass/api/futures/openInterest/chart?symbol=BTC&interval=1d&limit=30

# Funding Rates
GET /gateway/v1/proxy/coinglass/api/futures/fundingRate?symbol=BTC&exchange=binance

# Long/Short Ratio
GET /gateway/v1/proxy/coinglass/api/futures/longShortRatio?symbol=BTC

# Liquidations
GET /gateway/v1/proxy/coinglass/api/futures/liquidation?symbol=BTC&timeRange=1d
```

### TAAPI — Technical Indicators (2 credits)

200+ indicators available. Common ones:

```bash
# RSI
GET /gateway/v1/proxy/taapi/indicator/rsi?exchange=binance&symbol=BTC/USDT&interval=1d

# MACD
GET /gateway/v1/proxy/taapi/indicator/macd?exchange=binance&symbol=BTC/USDT&interval=1h

# Bollinger Bands
GET /gateway/v1/proxy/taapi/indicator/bbands?exchange=binance&symbol=BTC/USDT&interval=4h
```

Params: `exchange` (binance), `symbol` (BTC/USDT format), `interval` (1m, 5m, 15m, 1h, 4h, 1d, 1w, 1mo).

### SosoValue — ETF Flows (2 credits)

```bash
# BTC spot ETF flows
GET /gateway/v1/proxy/sosovalue/api/v1/etf/bitcoin-spot?date=2026-02-18

# ETH spot ETF flows
GET /gateway/v1/proxy/sosovalue/api/v1/etf/ethereum-spot?date=2026-02-18
```

### CryptoQuant — On-Chain Metrics (3 credits)

```bash
# Exchange Flows Netflow
GET /gateway/v1/proxy/cryptoquant/v1/btc/exchange-flows/netflow?window=day&limit=30

# Miner Revenue
GET /gateway/v1/proxy/cryptoquant/v1/btc/miner-revenue?window=day

# SOPR (Spent Output Profit Ratio)
GET /gateway/v1/proxy/cryptoquant/v1/btc/sopr?window=day

# NUPL (Net Unrealized Profit/Loss)
GET /gateway/v1/proxy/cryptoquant/v1/btc/nupl?window=day
```
