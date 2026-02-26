# Wallet Data — Endpoint Reference

<!-- Hermod /v1/wallet/* — standardized wallet data endpoints -->

## Endpoints

All endpoints are under `/v1/wallet/`. Response envelope: `{"data": [...], "meta": {...}}`.

| Endpoint | Description | Key Params | Cost |
|----------|-------------|------------|------|
| `GET /balance` | Get wallet balance | `address` (required) | 1 credit |
| `GET /history` | Get wallet transaction history | `address` (required), `chain`, `limit`, `offset` | 1 credit |
| `GET /labels` | Get wallet labels | `address` (required) | 1 credit |
| `POST /labels/batch` | Batch get wallet labels | body (required) | 1 credit |
| `GET /nft` | Get wallet NFTs | `address` (required), `chain`, `limit` | 1 credit |
| `GET /pnl` | Get wallet PnL | `address` (required) | 1 credit |
| `GET /search` | Search wallets | `q` (required) | 1 credit |
| `GET /tokens` | Get wallet token holdings | `address` (required), `chain` | 1 credit |
| `GET /top` | Get top/ranked wallets | `metric` (required), `limit`, `offset` | 1 credit |
| `GET /transfers` | Get wallet transfers | `address` (required), `chain`, `limit` | 1 credit |

### history — Valid Parameter Values

**`chain`**: `eth`, `bsc`, `matic`, `avax`, `ftm`, `arb`, `op`

### nft — Valid Parameter Values

**`chain`**: `eth`, `bsc`, `polygon`, `avalanche`, `fantom`, `arbitrum`, `optimism`

### tokens — Valid Parameter Values

**`chain`**: `eth`, `bsc`, `matic`, `avax`, `ftm`, `arb`, `op`

### top — Valid Parameter Values

**`metric`**: `balance`, `pnl`, `hyperliquid_whales`

### transfers — Valid Parameter Values

**`chain`**: `eth`, `solana`

### Chain Support

| Endpoint | Supported Chains |
|----------|-----------------|
| `history` | Chain filter using DeBank chain IDs |
| `nft` | Blockchain identifier (Moralis chain IDs) |
| `tokens` | Chain filter using DeBank chain IDs |
| `transfers` | eth, solana |

