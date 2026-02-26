# Onchain Data — Endpoint Reference

<!-- Hermod /v1/onchain/* — standardized onchain data endpoints -->

## Endpoints

All endpoints are under `/v1/onchain/`. Response envelope: `{"data": [...], "meta": {...}}`.

| Endpoint | Description | Key Params | Cost |
|----------|-------------|------------|------|
| `POST /query` | Execute structured query on blockchain data | body (required) | 5 credits |
| `POST /sql` | Execute raw SQL query | body (required) | 5 credits |
| `GET /tx` | Get transaction by hash | `hash` (required), `chain` (required) | 5 credits |

### tx — Valid Parameter Values

**`chain`**: `ethereum`, `goerli`, `sepolia`, `polygon`, `bsc`, `arbitrum`, `optimism`, `base`, `avalanche`, `fantom`, `linea`

### Chain Support

| Endpoint | Supported Chains |
|----------|-----------------|
| `tx` | Blockchain (Etherscan V2 chain name) |

