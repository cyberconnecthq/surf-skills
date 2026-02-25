# OnchainSQL — Database Reference

## Allowed Databases

Only the following databases are accessible. All table references must use `database.table` format.

---

### ethereum

Raw Ethereum blockchain data (~3.2B rows, 2015-present).

**Primary Table: `ethereum.transactions`**

| Column | Type | Description |
|--------|------|-------------|
| block_date | Date | **PARTITION KEY — always filter by this for time ranges** |
| block_number | UInt64 | Block number |
| block_timestamp | DateTime64(3) | Exact timestamp |
| block_hash | String | Block hash |
| transaction_hash | String | **PRIMARY KEY** |
| transaction_index | UInt32 | Position in block |
| nonce | UInt64 | Sender's nonce |
| from_address | String | Sender (0x...) |
| to_address | String | Recipient (0x...) |
| value | UInt256 | ETH in **wei** (divide by 1e18 for ETH) |
| gas | UInt64 | Gas limit |
| gas_price | UInt64 | Gas price in **wei** (divide by 1e9 for Gwei) |
| input | String | Calldata (0x...) |
| max_fee_per_gas | UInt64 | EIP-1559 max fee |
| max_priority_fee_per_gas | UInt64 | EIP-1559 priority fee |
| transaction_type | UInt64 | 0=legacy, 1=access_list, 2=EIP-1559, 3=blob, 4=EIP-7702 |
| receipt_cumulative_gas_used | UInt64 | Cumulative gas in block |
| receipt_gas_used | UInt64 | Gas actually used by tx |
| receipt_contract_address | String | Created contract (if deploy tx) |
| receipt_status | UInt64 | 1=success, 0=reverted |
| receipt_effective_gas_price | UInt64 | Effective gas price paid |
| max_fee_per_blob_gas | UInt64 | EIP-4844 blob fee |
| blob_versioned_hashes | Array(String) | EIP-4844 blob hashes |

**Partitioning:** Monthly by `toYYYYMM(block_date)`

---

### dex_ethereum

Decoded DEX trading data on Ethereum (~470M rows, 2018-present).

**Primary Table: `dex_ethereum.trades`**

| Column | Type | Description |
|--------|------|-------------|
| blockchain | String | Always "ethereum" |
| project | String | DEX name: uniswap, fluid, curve, native, pancakeswap, sushiswap, balancer, ekubo |
| version | String | Protocol version (v1, v2, v3, v4) |
| block_time | DateTime64(3) | **PRIMARY KEY — always filter by this, NOT block_date** |
| block_date | Date | Date only (**NOT indexed — avoid filtering on this!**) |
| block_number | UInt64 | Block number |
| token_pair | String | Format: "TOKEN_A-TOKEN_B" (hyphen-separated) |
| token_bought_symbol | String | Symbol received |
| token_sold_symbol | String | Symbol sent |
| token_bought_amount | Float64 | Amount received |
| token_sold_amount | Float64 | Amount sent |
| amount_usd | Float64 | Trade value in USD |
| taker | String | Swap initiator (0x...) |
| maker | String | Liquidity provider (0x...) |
| tx_hash | String | Transaction hash |

**Partitioning:** Monthly by `toYYYYMM(block_time)`

---

### dex_base

DEX trading data on Base chain. **Same schema as `dex_ethereum.trades`.**

---

### solana

Solana blockchain data.

**Key Tables:**
- `solana.transactions` — Solana transactions
- `solana.token_transfers` — SPL token transfers

---

### polymarket_polygon

Polymarket prediction market data on Polygon.

**Key Tables:**
- `polymarket_polygon.trades` — Market trades
- `polymarket_polygon.markets` — Market metadata

---

## Performance Rules (CRITICAL)

1. **`ethereum.transactions`**: ALWAYS filter by `block_date` (partition key) for time ranges
   - Good: `WHERE block_date >= '2025-01-01' AND block_date < '2025-02-01'`
   - Bad: `WHERE block_timestamp > '2025-01-01'` (full scan!)

2. **`dex_ethereum.trades`**: ALWAYS filter by `block_time` (primary key), NOT `block_date`
   - Good: `WHERE block_time >= today() - 7`
   - Bad: `WHERE block_date >= today() - 7` (not indexed!)

3. Both use monthly partitioning — narrow your time range as much as possible

## Query Constraints

- Only `SELECT` and `WITH` (CTE) statements allowed
- No `INSERT`, `UPDATE`, `DELETE`, `ALTER`, `DROP`, `CREATE`
- No multi-statement queries (no semicolons between statements)
- Max 10,000 rows per query (default 1,000)
- 30-second execution timeout
- 5 credits per query
