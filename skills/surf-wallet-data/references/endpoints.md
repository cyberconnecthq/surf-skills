# Wallet Data — Endpoint Reference

## Semantic Endpoints

Base path: `/gateway/v1/wallet`. Cost: 1-2 credits.

Each endpoint proxies to a specific upstream provider.

### GET /balance (upstream: DeBank)
Get wallet balance. Params: `address` (required).

### GET /token-list (upstream: DeBank)
List token holdings. Params: `address` (required).

### GET /transfer (upstream: Etherscan)
Get transfer history. Params: `address` (required), `chain` (optional: eth, bsc, polygon, etc.), `page` (optional), `offset` (optional), `sort` (optional: asc, desc).

### GET /trading-history (upstream: DeBank)
Get DEX trading history. Params: `address` (required).

### GET /transaction-history (upstream: Etherscan)
Get raw transaction history. Params: `address` (required), `chain` (optional), `page` (optional), `offset` (optional).

### GET /label/{address} (upstream: Recon)
Look up address label (exchange, whale, smart money, etc.). Cost: 1 credit.

### POST /label/batch (upstream: Recon)
Batch label lookup. Body: `{"addresses": ["0x...", "0x..."]}`. Cost: 2 credits.

### GET /entity/search (upstream: Recon)
Search entities by name. Params: `query` (required, e.g. "binance"). Cost: 2 credits.

---

## Proxy Endpoints (Advanced)

For granular wallet data, use proxy routes at `/gateway/v1/proxy/{service}/...`.

### DeBank — Cross-Chain Wallet Portfolio (5 credits)

Rate limit: 5 req/sec.

```bash
# Total cross-chain balance (USD value)
GET /gateway/v1/proxy/debank/v1/user/total_balance?id={ADDRESS}

# All token balances (cross-chain)
GET /gateway/v1/proxy/debank/v1/user/all_token_list?id={ADDRESS}

# All DeFi positions (cross-chain)
GET /gateway/v1/proxy/debank/v1/user/all_complex_protocol_list?id={ADDRESS}

# Single-chain token balances
GET /gateway/v1/proxy/debank/v1/user/token_list?id={ADDRESS}&chain_id={CHAIN_ID}

# Token authorizations/approvals (security audit)
GET /gateway/v1/proxy/debank/v1/user/token_authorized_list?id={ADDRESS}&chain_id={CHAIN_ID}

# Active chains for address
GET /gateway/v1/proxy/debank/v1/user/used_chain_list?id={ADDRESS}

# Transaction history
GET /gateway/v1/proxy/debank/v1/user/history_list?id={ADDRESS}&chain_id={CHAIN_ID}

# Token metadata & price
GET /gateway/v1/proxy/debank/v1/token?chain_id={CHAIN_ID}&id={TOKEN_ADDRESS}
```

Chain IDs: `eth`, `bsc`, `matic`, `arb`, `op`, `base`, `avax`, `ftm`, `xdai`, `era`, `linea`, `scrl`, `blast`, `sonic`

### Etherscan — EVM Chain Analytics (4 credits)

```bash
# Transaction by hash
GET /gateway/v1/proxy/etherscan/v2/api?chainid=1&module=proxy&action=eth_getTransactionByHash&txhash={TX_HASH}

# Transaction receipt
GET /gateway/v1/proxy/etherscan/v2/api?chainid=1&module=proxy&action=eth_getTransactionReceipt&txhash={TX_HASH}

# Transaction history
GET /gateway/v1/proxy/etherscan/v2/api?chainid=1&module=account&action=txlist&address={ADDRESS}&startblock=0&endblock=99999999&page=1&offset=100&sort=desc

# Token transfers
GET /gateway/v1/proxy/etherscan/v2/api?chainid=1&module=account&action=tokentx&address={ADDRESS}&page=1&offset=100&sort=desc

# Contract ABI
GET /gateway/v1/proxy/etherscan/v2/api?chainid=1&module=contract&action=getabi&address={CONTRACT_ADDRESS}
```

Chain IDs: 1 (Ethereum), 137 (Polygon), 42161 (Arbitrum), 10 (Optimism), 8453 (Base), 56 (BNB)

### Recon — Address Intelligence (1 credit)

```bash
# Single address lookup
GET /gateway/v1/proxy/recon/intel/address/{ADDRESS}

# Batch address lookup (up to 500)
POST /gateway/v1/proxy/recon/intel/addresses/batch
Body: {"addresses": ["0x...", "0x..."]}

# Entity search
GET /gateway/v1/proxy/recon/intel/search?query={QUERY}
```

Response includes: entity type (cex, fund, defi, bridge, whale, contract), entity name, label.

### Moralis — Multi-Chain Token Data (2 credits)

```bash
# Token holders (top by balance)
GET /gateway/v1/proxy/moralis/api/v2.2/erc20/{TOKEN_ADDRESS}/owners?chain={CHAIN}&order=DESC&limit=100

# Token metadata
GET /gateway/v1/proxy/moralis/api/v2.2/erc20/metadata?chain={CHAIN}&addresses[]={TOKEN_ADDRESS}

# Wallet token balances
GET /gateway/v1/proxy/moralis/api/v2.2/{WALLET_ADDRESS}/erc20?chain={CHAIN}

# Token transfers
GET /gateway/v1/proxy/moralis/api/v2.2/erc20/{TOKEN_ADDRESS}/transfers?chain={CHAIN}&limit=100
```

Chains: `eth`, `base`, `arbitrum`, `optimism`, `polygon`, `bsc`. Pagination: cursor-based.

### Solscan — Solana Blockchain (4 credits)

```bash
# Account transactions
GET /gateway/v1/proxy/solscan/v2.0/account/transactions?address={ADDRESS}&page=1&page_size=100

# Account transfers
GET /gateway/v1/proxy/solscan/v2.0/account/transfer?address={ADDRESS}&page=1&page_size=100

# Token holders
GET /gateway/v1/proxy/solscan/v2.0/token/holders?token={TOKEN_MINT}&page=1&page_size=100

# Token transfers
GET /gateway/v1/proxy/solscan/v2.0/token/transfer?token={TOKEN_MINT}&page=1&page_size=100

# Token price & markets
GET /gateway/v1/proxy/solscan/v2.0/token/price?token={TOKEN_MINT}
GET /gateway/v1/proxy/solscan/v2.0/token/markets?token={TOKEN_MINT}

# Transaction details
GET /gateway/v1/proxy/solscan/v2.0/transaction/detail?tx={TX_SIGNATURE}

# Portfolio
GET /gateway/v1/proxy/solscan/v2.0/account/portfolio?address={ADDRESS}
```

### Alchemy — Multi-Chain RPC (1 credit)

Proxy paths: `alchemy-eth`, `alchemy-base`, `alchemy-arb`, `alchemy-opt`, `alchemy-polygon`, `alchemy-solana`

```bash
# Token balances (JSON-RPC POST)
POST /gateway/v1/proxy/alchemy-eth/
Body: {"jsonrpc":"2.0","method":"alchemy_getTokenBalances","params":["{WALLET_ADDRESS}"],"id":1}

# Token metadata
POST /gateway/v1/proxy/alchemy-eth/
Body: {"jsonrpc":"2.0","method":"alchemy_getTokenMetadata","params":["{TOKEN_ADDRESS}"],"id":1}
```
