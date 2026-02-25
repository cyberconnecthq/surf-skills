# Token Data — Endpoint Reference

## Semantic Endpoints

Base path: `/gateway/v1/token-data`. Cost: 1 credit each.

Each endpoint proxies to a specific upstream provider. Parameter names vary by upstream.

### GET /holder (upstream: Moralis)
Get token holder distribution. Params: `token` (required, ERC20 contract address), `chain` (required: eth, base, arbitrum, optimism, polygon, bsc), `limit` (optional).

### GET /transfer (upstream: Etherscan)
Get token transfer data. Params: `token` (required, contract address), `chain` (required: eth, base, arbitrum, etc.), `page` (optional), `offset` (optional).

### GET /exchange-flow (upstream: CryptoQuant)
Get exchange inflow/outflow. Params: `asset` (required: btc, eth), `flow_type` (required: netflow, inflow, outflow), `exchange` (optional: all_exchange, binance, etc.), `window` (optional: day, hour), `limit` (optional).

### GET /etf-flow (upstream: SoSoValue)
Get ETF flow data. Params: `type` (required: us-btc-spot, us-eth-spot).

### GET /exchange-reserve (upstream: CryptoQuant)
Get exchange reserve levels. Params: `asset` (required: btc, eth), `exchange` (optional: all_exchange), `window` (optional: day, hour), `limit` (optional).

---

## Proxy Endpoints (Advanced)

### Moralis — ERC20 Token Holders (2 credits)

```bash
# Top holders by balance
GET /gateway/v1/proxy/moralis/api/v2.2/erc20/{TOKEN_ADDRESS}/owners?chain={CHAIN}&order=DESC&limit=100

# Token metadata (name, symbol, decimals, total supply)
GET /gateway/v1/proxy/moralis/api/v2.2/erc20/metadata?chain={CHAIN}&addresses[]={TOKEN_ADDRESS}

# Token transfers
GET /gateway/v1/proxy/moralis/api/v2.2/erc20/{TOKEN_ADDRESS}/transfers?chain={CHAIN}&limit=100
```

Chains: `eth`, `base`, `arbitrum`, `optimism`, `polygon`, `bsc`. Pagination: cursor-based.

Response (holders):
```json
{
  "result": [
    {
      "owner_address": "0x...",
      "balance": "1000000000000000000",
      "balance_formatted": "1.0",
      "percentage_relative_to_total_supply": 0.5,
      "is_contract": false
    }
  ],
  "cursor": "..."
}
```

### CryptoQuant — Exchange Flows & On-Chain Metrics (3 credits)

```bash
# Exchange Netflow
GET /gateway/v1/proxy/cryptoquant/v1/btc/exchange-flows/netflow?window=day&limit=30

# SOPR (Spent Output Profit Ratio)
GET /gateway/v1/proxy/cryptoquant/v1/btc/sopr?window=day

# NUPL (Net Unrealized Profit/Loss)
GET /gateway/v1/proxy/cryptoquant/v1/btc/nupl?window=day
```

### Solscan — Solana Token Data (4 credits)

```bash
# Token holders
GET /gateway/v1/proxy/solscan/v2.0/token/holders?token={TOKEN_MINT}&page=1&page_size=100

# Token transfers
GET /gateway/v1/proxy/solscan/v2.0/token/transfer?token={TOKEN_MINT}&page=1&page_size=100

# Token price & markets
GET /gateway/v1/proxy/solscan/v2.0/token/price?token={TOKEN_MINT}
GET /gateway/v1/proxy/solscan/v2.0/token/markets?token={TOKEN_MINT}
```

### SosoValue — ETF Flows (2 credits)

```bash
# BTC spot ETF flows and holdings
GET /gateway/v1/proxy/sosovalue/api/v1/etf/bitcoin-spot?date=2026-02-18

# ETH spot ETF flows
GET /gateway/v1/proxy/sosovalue/api/v1/etf/ethereum-spot?date=2026-02-18
```
