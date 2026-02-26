# OnchainSQL — Query Examples

## Ethereum Transactions

### Count recent transactions (use block_date for performance)
```sql
SELECT count()
FROM ethereum.transactions
WHERE block_date >= '2025-02-01' AND block_date < '2025-03-01'
```

### Look up a specific transaction by hash
```sql
SELECT transaction_hash, from_address, to_address,
       value / 1e18 AS eth_value,
       receipt_gas_used, receipt_status
FROM ethereum.transactions
WHERE transaction_hash = '0x...'
```

### Transaction history for an address (filter by block_date!)
```sql
SELECT transaction_hash, block_number, from_address, to_address,
       value / 1e18 AS eth_value, receipt_status
FROM ethereum.transactions
WHERE block_date >= today() - 30
  AND (from_address = lower('0x...') OR to_address = lower('0x...'))
ORDER BY block_number DESC
LIMIT 100
```

### Contract interaction frequency
```sql
SELECT to_address, count() AS call_count,
       sum(receipt_gas_used) AS total_gas
FROM ethereum.transactions
WHERE block_date >= today() - 7
  AND from_address = lower('0x...')
GROUP BY to_address
ORDER BY call_count DESC
LIMIT 20
```

### Gas price trends (Gwei)
```sql
SELECT
  block_number,
  avg(gas_price) / 1e9 AS avg_gas_gwei,
  max(gas_price) / 1e9 AS max_gas_gwei,
  count() AS tx_count
FROM ethereum.transactions
WHERE block_date = today()
  AND block_number >= 19500000
GROUP BY block_number
ORDER BY block_number DESC
LIMIT 50
```

### Contract deployments
```sql
SELECT transaction_hash, from_address, receipt_contract_address, block_number
FROM ethereum.transactions
WHERE block_date >= today() - 7
  AND receipt_contract_address != ''
ORDER BY block_number DESC
LIMIT 50
```

---

## DEX Analysis (dex_ethereum)

### Top trading pairs by volume (filter by block_time!)
```sql
SELECT
  token_pair,
  count() AS trade_count,
  sum(amount_usd) AS volume_usd
FROM dex_ethereum.trades
WHERE block_time >= today() - 7
GROUP BY token_pair
ORDER BY volume_usd DESC
LIMIT 20
```

### DEX market share this week
```sql
SELECT
  project, version,
  count() AS trade_count,
  sum(amount_usd) AS volume_usd
FROM dex_ethereum.trades
WHERE block_time >= today() - 7
GROUP BY project, version
ORDER BY volume_usd DESC
LIMIT 20
```

### Recent trades for a specific pair
```sql
SELECT block_time, token_bought_symbol, token_bought_amount,
       token_sold_symbol, token_sold_amount, amount_usd, tx_hash
FROM dex_ethereum.trades
WHERE block_time >= today() - 1
  AND token_pair = 'USDC-WETH'
ORDER BY block_time DESC
LIMIT 50
```

### Whale trades (>$100k)
```sql
SELECT block_time, token_pair, amount_usd, taker, project, tx_hash
FROM dex_ethereum.trades
WHERE block_time >= today() - 1
  AND amount_usd > 100000
ORDER BY amount_usd DESC
LIMIT 100
```

### Address trading activity
```sql
SELECT token_pair, project,
       count() AS trades,
       sum(amount_usd) AS total_volume
FROM dex_ethereum.trades
WHERE block_time >= today() - 30
  AND taker = lower('0x...')
GROUP BY token_pair, project
ORDER BY total_volume DESC
LIMIT 20
```

---

## Advanced / CTE Patterns

### Active traders this week
```sql
WITH active AS (
  SELECT DISTINCT taker
  FROM dex_ethereum.trades
  WHERE block_time >= today() - 7
)
SELECT count() AS active_traders FROM active
```

### Cross-table: match DEX trades to raw transactions
```sql
SELECT
  t.transaction_hash,
  t.from_address,
  t.receipt_gas_used,
  d.token_pair,
  d.amount_usd,
  d.project
FROM ethereum.transactions t
JOIN dex_ethereum.trades d ON t.transaction_hash = d.tx_hash
WHERE t.block_date = today()
  AND d.block_time >= today()
  AND d.amount_usd > 50000
ORDER BY d.amount_usd DESC
LIMIT 20
```

---

## Polymarket

### Recent Polymarket trades
```sql
SELECT * FROM polymarket_polygon.trades
ORDER BY block_number DESC
LIMIT 20
```

---

## Common Mistakes to Avoid

```sql
-- BAD: filtering dex_ethereum by block_date (not indexed!)
SELECT * FROM dex_ethereum.trades WHERE block_date >= today() - 7

-- GOOD: filter by block_time instead
SELECT * FROM dex_ethereum.trades WHERE block_time >= today() - 7

-- BAD: filtering ethereum.transactions by block_timestamp (full scan)
SELECT * FROM ethereum.transactions WHERE block_timestamp >= '2025-01-01'

-- GOOD: filter by block_date (partition key)
SELECT * FROM ethereum.transactions WHERE block_date >= '2025-01-01'

-- BAD: value displayed as raw wei
SELECT value FROM ethereum.transactions

-- GOOD: convert wei to ETH
SELECT value / 1e18 AS eth_value FROM ethereum.transactions
```
