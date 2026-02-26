# Token Data — Endpoint Reference

<!-- Hermod /v1/token/* — standardized token data endpoints -->

## Endpoints

All endpoints are under `/v1/token/`. Response envelope: `{"data": [...], "meta": {...}}`.

| Endpoint | Description | Key Params | Cost |
|----------|-------------|------------|------|
| `GET /holders` | Get token holders | `address` (required), `chain` (required), `limit`, `offset` | 1 credit |
| `GET /info` | Get token metadata | `address` (required), `chain` | 1 credit |
| `GET /metrics` | Get token time-series metrics | `asset` (required), `metric` (required), `window`, `limit`, `exchange`, `type` | 1 credit |
| `GET /search` | Search tokens | `q` (required) | 1 credit |
| `GET /top` | Get top/ranked tokens | `metric` (required), `limit`, `offset` | 1 credit |
| `GET /top-traders` | Get top traders for a token | `address` (required) | 1 credit |
| `GET /transfers` | Get token transfers | `address` (required), `chain` (required), `limit`, `sort` | 1 credit |
| `GET /unlock` | Get token unlock schedule | `id` (required), `timeframe` | 1 credit |

### holders — Valid Parameter Values

**`chain`**: `eth`, `bsc`, `polygon`, `avalanche`, `fantom`, `arbitrum`, `optimism`, `solana`

### info — Valid Parameter Values

**`chain`**: `eth`, `bsc`, `polygon`, `avalanche`, `fantom`, `arbitrum`, `optimism`, `solana`

### metrics — Valid Parameter Values

**`metric`**: `exchange_flow`, `etf_flow`, `exchange_reserve`

**`window`**: `day`, `hour`

**`type`**: `us-btc-spot`, `us-eth-spot`

### top — Valid Parameter Values

**`metric`**: `volume`, `gainers`, `losers`, `exchange_inflow`, `exchange_outflow`, `mindshare`

### transfers — Valid Parameter Values

**`chain`**: `eth`, `solana`

**`sort`**: `asc`, `desc`

### Chain Support

| Endpoint | Supported Chains |
|----------|-----------------|
| `holders` | arbitrum, avalanche, bsc, eth, fantom, optimism, polygon, solana |
| `info` | arbitrum, avalanche, bsc, eth, fantom, optimism, polygon, solana |
| `transfers` | eth, solana |

