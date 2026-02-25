---
name: surf-onchain-sql
description: Query on-chain blockchain data using SQL via ClickHouse
tools: ["bash"]
---

# OnchainSQL — On-chain Data Query

Query blockchain data directly using SQL against ClickHouse databases via the Hermod API Gateway.

## When to Use

Use this skill when you need to:
- Query raw blockchain data (transactions, logs, token transfers)
- Analyze DEX trading activity (swaps, liquidity, volume)
- Investigate specific addresses, contracts, or transactions on-chain
- Run custom aggregations over blockchain data
- Query Polymarket prediction market data

## Available Databases

| Database | Description |
|----------|-------------|
| `ethereum` | Raw Ethereum blockchain data (blocks, transactions, logs, traces) |
| `solana` | Solana blockchain data |
| `dex_ethereum` | DEX trading data on Ethereum (swaps, pools, liquidity) |
| `dex_base` | DEX trading data on Base chain |
| `polymarket_polygon` | Polymarket prediction market data on Polygon |

## CLI Usage

```bash
# Check setup
surf-onchain-sql/scripts/surf-onchain --check-setup

# Run a SQL query
surf-onchain-sql/scripts/surf-onchain query "SELECT count() FROM ethereum.transactions WHERE block_number > 19000000"

# Run with custom row limit (default 1000, max 10000)
surf-onchain-sql/scripts/surf-onchain query "SELECT * FROM ethereum.transactions LIMIT 10" --max-rows 5000
```

## Query Rules

1. **Only SELECT and WITH (CTE) statements** — no writes allowed
2. **Table names must be fully qualified** — use `database.table` format (e.g., `ethereum.transactions`)
3. **Max 10,000 rows** per query — default limit is 1,000
4. **30-second timeout** per query
5. **5 credits** per query

## Response Format

```json
{
  "success": true,
  "data": {
    "columns": ["hash", "from_address", "to_address", "value"],
    "rows": [["0x123...", "0xabc...", "0xdef...", "1000000000000000000"]],
    "row_count": 1
  }
}
```

## Performance Rules (CRITICAL)

- **`ethereum.transactions`**: ALWAYS filter by `block_date` (partition key) for time ranges. Never filter by `block_timestamp` alone — it causes full table scans on 3.2B rows
- **`dex_ethereum.trades`**: ALWAYS filter by `block_time` (primary key). Never filter by `block_date` — it is NOT indexed
- **Value fields**: `ethereum.transactions.value` is in wei (UInt256). Divide by `1e18` for ETH, divide `gas_price` by `1e9` for Gwei

## Tips

- Always include a `LIMIT` clause to control result size
- Use CTEs (`WITH ... AS`) for complex queries
- Narrow your time range as much as possible — both tables use monthly partitioning
- `dex_ethereum.trades.token_pair` format is "TOKEN_A-TOKEN_B" (hyphen-separated)
- Known DEX projects: uniswap, fluid, curve, native, pancakeswap, sushiswap, balancer, ekubo
- See `references/databases.md` for full column schemas and `references/examples.md` for query patterns
