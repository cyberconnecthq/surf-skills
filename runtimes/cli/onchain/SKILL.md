---
name: surf-onchain
description: Query on-chain blockchain data with SQL — Ethereum transactions, DEX trades, Solana, Polymarket
tools: ["bash"]
---

# Onchain Data — SQL Queries on Blockchain Data

Execute SQL queries against on-chain blockchain data (Ethereum transactions, DEX trades, Solana, Polymarket) via ClickHouse. Supports raw SQL, structured queries, and transaction lookups. All data via the Hermod API Gateway.

## Quick Reference

| Command | Description | Cost |
|---------|-------------|------|
| `sql --sql "SELECT ..." [--max-rows 100]` | Execute raw SQL query | 5 |
| `query --body '{...}'` | Execute structured query (JSON) | 5 |
| `tx --hash 0x... --chain ethereum` | Look up transaction by hash | 5 |

## Available Databases

| Database | Table(s) | Data | Time Filter |
|----------|----------|------|-------------|
| `ethereum` | `ethereum.transactions` | Raw Ethereum txs (2015-present, ~3.2B rows) | `block_date` (partition key) |
| `dex_ethereum` | `dex_ethereum.trades` | Decoded DEX trades on Ethereum (2018-present, ~470M rows) | `block_time` (primary key) |
| `dex_base` | `dex_base.trades` | DEX trades on Base (same schema as dex_ethereum) | `block_time` |
| `solana` | `solana.transactions`, `solana.token_transfers` | Solana blockchain data | -- |
| `polymarket_polygon` | `polymarket_polygon.trades`, `polymarket_polygon.markets` | Polymarket prediction markets | -- |

## Performance Rules (CRITICAL)

- **`ethereum.transactions`**: ALWAYS filter by `block_date` (partition key). Never filter by `block_timestamp` alone (causes full scan).
- **`dex_ethereum.trades` / `dex_base.trades`**: ALWAYS filter by `block_time` (primary key). Never filter by `block_date` (not indexed).
- **Narrow time ranges**: Both use monthly partitioning. Query the smallest window possible.
- **Convert units**: ETH `value` is in wei (divide by 1e18). Gas price is in wei (divide by 1e9 for Gwei).

## Query Constraints

- Only `SELECT` and `WITH` (CTE) statements allowed
- Max 10,000 rows per query (default 1,000)
- 30-second execution timeout
- 5 credits per query

## Common Tasks

### Task: Analyze DEX Trading Volume

Find top trading pairs, DEX market share, and volume trends.

```bash
# Top trading pairs by volume (last 7 days)
surf-onchain sql --sql "SELECT token_pair, count() AS trade_count, sum(amount_usd) AS volume_usd FROM dex_ethereum.trades WHERE block_time >= today() - 7 GROUP BY token_pair ORDER BY volume_usd DESC LIMIT 20"

# DEX market share this week
surf-onchain sql --sql "SELECT project, version, count() AS trade_count, sum(amount_usd) AS volume_usd FROM dex_ethereum.trades WHERE block_time >= today() - 7 GROUP BY project, version ORDER BY volume_usd DESC LIMIT 20"

# Recent trades for a specific pair (e.g., USDC-WETH)
surf-onchain sql --sql "SELECT block_time, token_bought_symbol, token_bought_amount, token_sold_symbol, token_sold_amount, amount_usd, tx_hash FROM dex_ethereum.trades WHERE block_time >= today() - 1 AND token_pair = 'USDC-WETH' ORDER BY block_time DESC LIMIT 50"
```

**What to look for:** Uniswap v3 typically dominates volume. Sudden shifts in market share may signal liquidity migration. Unusual pair volume can indicate new token launches or exit scams.

### Task: Detect Whale DEX Activity

Find large trades that may signal institutional or whale activity.

```bash
# Whale trades over $100k in last 24 hours
surf-onchain sql --sql "SELECT block_time, token_pair, amount_usd, taker, project, tx_hash FROM dex_ethereum.trades WHERE block_time >= today() - 1 AND amount_usd > 100000 ORDER BY amount_usd DESC LIMIT 100"

# Whale trades over $500k for a specific token
surf-onchain sql --sql "SELECT block_time, token_pair, amount_usd, taker, project, tx_hash FROM dex_ethereum.trades WHERE block_time >= today() - 7 AND amount_usd > 500000 AND (token_bought_symbol = 'WETH' OR token_sold_symbol = 'WETH') ORDER BY amount_usd DESC LIMIT 50"
```

**What to look for:** Repeated large sells from the same `taker` address may indicate distribution. Cluster of whale buys can signal accumulation. Cross-reference taker addresses with known wallets.

### Task: Analyze Token Transfer and Wallet Activity

Track an address's transaction history and contract interactions.

```bash
# Transaction history for an address (last 30 days)
surf-onchain sql --sql "SELECT transaction_hash, block_number, from_address, to_address, value / 1e18 AS eth_value, receipt_status FROM ethereum.transactions WHERE block_date >= today() - 30 AND (from_address = lower('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045') OR to_address = lower('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045')) ORDER BY block_number DESC LIMIT 100"

# What contracts does an address interact with most?
surf-onchain sql --sql "SELECT to_address, count() AS call_count, sum(receipt_gas_used) AS total_gas FROM ethereum.transactions WHERE block_date >= today() - 7 AND from_address = lower('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045') GROUP BY to_address ORDER BY call_count DESC LIMIT 20"

# DEX trading activity for an address
surf-onchain sql --sql "SELECT token_pair, project, count() AS trades, sum(amount_usd) AS total_volume FROM dex_ethereum.trades WHERE block_time >= today() - 30 AND taker = lower('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045') GROUP BY token_pair, project ORDER BY total_volume DESC LIMIT 20"
```

**What to look for:** High-frequency contract interactions reveal DeFi strategy. Compare ETH outflows vs inflows. Check `receipt_status` for failed transactions (bots or MEV).

### Task: Monitor Gas and Network Activity

Track Ethereum network congestion and gas trends.

```bash
# Gas price trends by block (today)
surf-onchain sql --sql "SELECT block_number, avg(gas_price) / 1e9 AS avg_gas_gwei, max(gas_price) / 1e9 AS max_gas_gwei, count() AS tx_count FROM ethereum.transactions WHERE block_date = today() AND block_number >= 19500000 GROUP BY block_number ORDER BY block_number DESC LIMIT 50"

# Transaction count this month
surf-onchain sql --sql "SELECT count() FROM ethereum.transactions WHERE block_date >= '2025-02-01' AND block_date < '2025-03-01'"

# Recent contract deployments
surf-onchain sql --sql "SELECT transaction_hash, from_address, receipt_contract_address, block_number FROM ethereum.transactions WHERE block_date >= today() - 7 AND receipt_contract_address != '' ORDER BY block_number DESC LIMIT 50"
```

**What to look for:** Sustained high gas prices signal network congestion or popular mint/launch. Spike in contract deployments may indicate new protocol launches or scam token factories.

### Task: Cross-Chain DEX Comparison

Compare DEX activity between Ethereum and Base.

```bash
# Ethereum DEX volume by project
surf-onchain sql --sql "SELECT project, count() AS trades, sum(amount_usd) AS volume_usd FROM dex_ethereum.trades WHERE block_time >= today() - 7 GROUP BY project ORDER BY volume_usd DESC LIMIT 10"

# Base DEX volume by project
surf-onchain sql --sql "SELECT project, count() AS trades, sum(amount_usd) AS volume_usd FROM dex_base.trades WHERE block_time >= today() - 7 GROUP BY project ORDER BY volume_usd DESC LIMIT 10"
```

**What to look for:** Compare total volumes to gauge L2 adoption. Rising Base volume relative to Ethereum signals L2 migration. Check which DEX protocols are gaining share on each chain.

### Task: Look Up a Specific Transaction

Get full details of a known transaction.

```bash
# By hash (quick lookup)
surf-onchain tx --hash 0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060 --chain ethereum

# By hash with SQL (more fields)
surf-onchain sql --sql "SELECT transaction_hash, from_address, to_address, value / 1e18 AS eth_value, receipt_gas_used, receipt_status FROM ethereum.transactions WHERE transaction_hash = '0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060'"
```

### Task: Active Trader Analysis

Count unique active traders and identify power users.

```bash
# Count active DEX traders this week
surf-onchain sql --sql "WITH active AS (SELECT DISTINCT taker FROM dex_ethereum.trades WHERE block_time >= today() - 7) SELECT count() AS active_traders FROM active"

# Cross-table: match DEX trades to raw transactions (whale trades with gas data)
surf-onchain sql --sql "SELECT t.transaction_hash, t.from_address, t.receipt_gas_used, d.token_pair, d.amount_usd, d.project FROM ethereum.transactions t JOIN dex_ethereum.trades d ON t.transaction_hash = d.tx_hash WHERE t.block_date = today() AND d.block_time >= today() AND d.amount_usd > 50000 ORDER BY d.amount_usd DESC LIMIT 20"
```

## Cross-Domain Workflows

### On-Chain Whale Activity + Social Signal

Combine on-chain whale detection with social monitoring for alpha.

```bash
# Find whale trades
surf-onchain sql --sql "SELECT block_time, token_pair, amount_usd, taker, project FROM dex_ethereum.trades WHERE block_time >= today() - 1 AND amount_usd > 500000 ORDER BY amount_usd DESC LIMIT 20"

# Check social buzz around the traded tokens (use surf-social)
surf-social search --query "WETH large trade" --limit 10
surf-social sentiment --id ethereum

# Check project fundamentals (use surf-project)
surf-project metrics --id uniswap --metric volume
```

## Tips

- **Always use the correct time filter.** `block_date` for `ethereum.transactions`, `block_time` for `dex_*.trades`. Using the wrong one causes slow full-table scans.
- **Convert units.** ETH value is in wei (divide by `1e18`). Gas price is in wei (divide by `1e9` for Gwei).
- **Token pairs use hyphens.** Format is `TOKEN_A-TOKEN_B` (e.g., `USDC-WETH`, `WBTC-WETH`).
- **DEX `project` values:** uniswap, fluid, curve, native, pancakeswap, sushiswap, balancer, ekubo.
- **Addresses must be lowercase.** Always wrap in `lower('0x...')`.
- **`--sql` requires quoting.** Wrap the full SQL string in double quotes. SQL is safely JSON-escaped via jq (or python3 fallback).
- **`--max-rows`** limits the maximum number of returned rows (default server-side: 1000, max: 10,000).
- **All output is JSON.** Data goes to stdout, errors to stderr.
- **5 credits per query** for all onchain endpoints.
- **Max 10,000 rows.** Use `LIMIT` to control result size.
