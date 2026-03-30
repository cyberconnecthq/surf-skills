---
name: onchain
description: >
  Raw on-chain data: transaction decode (QuickNode JSON-RPC, multi-chain), structured query (no-SQL),
  and SQL analytics on ClickHouse. Covers Ethereum, Base, Arbitrum, BSC, Tron, HyperEVM, Bitcoin, Tempo.
  Tables: DEX trades, transactions, traces, event logs, token transfers, blocks, prices,
  protocol fees/revenue, TVL, DeFi yields, bridge volume,
  prediction markets (Polymarket/Kalshi — trades, prices, leaderboards, user positions, categories),
  Hyperliquid perpetual futures, x402 payments, Tempo network metrics.
  Use for: transaction analysis, DEX volume queries, gas analysis, whale trade detection,
  custom SQL aggregations on historical blockchain data, structured blockchain queries,
  protocol fees and TVL comparison, yield farming analysis, prediction market analytics,
  perp funding rates, open interest, bridge flow analysis, Bitcoin UTXO analysis.
  Keywords: transaction, tx, decode, onchain, sql, dex, trades, volume, analytics, clickhouse,
  gas, whale, bridge, transfer, structured query, traces, event logs, fees, revenue, tvl,
  polymarket, kalshi, prediction market, betting, odds, hyperliquid, perp, funding rate, open interest,
  positions, leaderboard, category, yields, defi, bitcoin, utxo, arbitrum, bsc, tron, hyperevm, tempo,
  x402, payments, bridge volume.
---

<!-- @format -->

# Raw On-Chain Data Skill

Raw on-chain data access via four modes: transaction decode, structured query, SQL analytics, and schema discovery.

**IMPORTANT: Before writing any SQL query, query the schema endpoint to get column names and types for the tables you plan to use. See [Schema Discovery](#schema-discovery) below.**

## API Access

All onchain data flows through the `/proxy/onchain/*` route. Authentication is automatic.

**Frontend** (React hooks from `@surf-ai/sdk/react`):
```tsx
import { useOnchainSql, useOnchainTx, useOnchainSchema } from '@surf-ai/sdk/react'

const { data } = useOnchainSql({ sql: 'SELECT ...', max_rows: 100 })
const { data: tx } = useOnchainTx({ hash: '0x...', chain: 'ethereum' })
const { data: schema } = useOnchainSchema()
```

**Backend** (`@surf-ai/sdk/server`):
```js
const { dataApi } = require('@surf-ai/sdk/server')

const result = await dataApi.onchain.sql({ sql: 'SELECT ...', max_rows: 100 })
const tx = await dataApi.onchain.tx({ hash: '0x...', chain: 'ethereum' })
const schema = await dataApi.onchain.schema()
```

## Four Access Modes

| Mode                 | Endpoint | Method | Use Case                                                   |
| -------------------- | -------- | ------ | ---------------------------------------------------------- |
| Transaction Decode   | `tx`     | GET    | Single tx hash lookup via QuickNode JSON-RPC               |
| Structured Query     | `query`  | POST   | Filter/sort blockchain data without SQL (JSON body)        |
| SQL Analytics        | `sql`    | POST   | Complex aggregations on ClickHouse (GROUP BY, JOINs, etc.) |
| **Schema Discovery** | `schema` | GET    | List all tables with column names and types                |

### Supported Chains

- **Transaction decode (`tx`)**: `ethereum`, `polygon`, `bsc`, `arbitrum`, `optimism`, `base`, `avalanche`, `fantom`, `linea`, `cyber`
- **Structured query (`query`)**: `ethereum`, `base`, `solana`
- **SQL analytics (`sql`)**: All tables listed in the Table Index below

### Structured Query Sources

For the `query` endpoint, source format is `{chain}.{table}`:

| Source                                                          | Description      |
| --------------------------------------------------------------- | ---------------- |
| `ethereum.transactions` / `ethereum.traces`                     | Ethereum mainnet |
| `base.transactions` / `base.traces`                             | Base chain       |
| `solana.transactions`                                           | Solana           |
| `dex_ethereum.trades` / `dex_base.trades`                       | DEX trades       |
| `tokens_ethereum.base_transfers` / `tokens_base.base_transfers` | Token transfers  |

## ClickHouse SQL Analytics

### Database & Table Naming

**CRITICAL: ALWAYS use `agent.` prefix (e.g., `agent.ethereum_dex_trades`, NOT `ethereum_dex_trades`). Unqualified names will be rejected.**

### Table Index

Use the schema endpoint to discover columns before writing SQL. The Table Index below lists every table with row counts and **mandatory filter columns** — always filter by these to avoid timeouts on billion-row tables.

#### Ethereum

| Table                         | Rows    | Time Range | MUST Filter By                                        |
| ----------------------------- | ------- | ---------- | ----------------------------------------------------- |
| `agent.ethereum_dex_trades`   | ~484M   | 2018-11+   | `block_time` (PK) or `block_date` (partition)         |
| `agent.ethereum_transactions` | ~3.4B   | genesis+   | `block_date` (partition) or `transaction_hash` (PK)   |
| `agent.ethereum_traces`       | ~15.7B  | genesis+   | `block_date` (partition) + `transaction_hash` (bloom) |
| `agent.ethereum_event_logs`   | ~6.5B   | genesis+   | `block_date` (partition) + `address` (PK)             |
| `agent.ethereum_transfers`    | ~8.5B   | genesis+   | `contract_address` (PK) + `block_date` (partition)    |
| `agent.ethereum_fees_daily`   | ~35K    | genesis+   | `block_date` + `project` (small, safe to scan)        |
| `agent.ethereum_tvl_daily`    | ~78K    | 2019-08+   | `block_date` + `project` (small, safe to scan)        |
| `agent.ethereum_yields_daily` | ~11.4M  | 2020+      | `block_date` + `project` (or `pool_address`)          |

#### Base

| Table                     | Rows    | Time Range | MUST Filter By                                        |
| ------------------------- | ------- | ---------- | ----------------------------------------------------- |
| `agent.base_dex_trades`   | ~1.3B   | 2023-07+   | `block_time` (PK) or `block_date` (partition)         |
| `agent.base_transactions` | ~6.0B   | 2023-06+   | `block_date` (partition)                              |
| `agent.base_traces`       | ~139B   | 2023-06+   | `block_date` (partition) + `transaction_hash` (bloom) |
| `agent.base_event_logs`   | ~23.3B  | 2023-06+   | `block_date` (partition) + `address` (PK)             |
| `agent.base_transfers`    | ~7.5B   | 2023-06+   | `contract_address` (PK) + `block_date` (partition)    |
| `agent.base_tvl_daily`    | ~9.4K   | 2023-08+   | `block_date` + `project` (small, safe to scan)        |

#### Arbitrum

| Table                          | Rows    | Time Range | MUST Filter By                                        |
| ------------------------------ | ------- | ---------- | ----------------------------------------------------- |
| `agent.arbitrum_dex_trades`    | ~301M   | 2021-08+   | `block_time` (PK) or `block_date` (partition)         |
| `agent.arbitrum_transactions`  | ~2.5B   | 2021-08+   | `block_date` (partition)                              |
| `agent.arbitrum_traces`        | ~38.3B  | 2021-08+   | `block_date` (partition) + `transaction_hash` (bloom) |
| `agent.arbitrum_blocks`        | ~447M   | 2021-08+   | `date` or `number`                                    |
| `agent.arbitrum_event_logs`    | large   | 2021-08+   | `block_date` (partition) + `address` (PK)             |
| `agent.arbitrum_transfers`     | ~312M   | 2021-08+   | `contract_address` (PK) + `block_date` (partition)    |
| `agent.arbitrum_prices_day`    | ~274K   | 2021-08+   | `block_date` + `contract_address` (small)             |
| `agent.arbitrum_prices_hour`   | ~5.5M   | 2021-08+   | `hour` + `contract_address`                           |
| `agent.arbitrum_tvl_daily`     | ~42     | recent     | scan (tiny)                                           |

#### BSC (BNB Smart Chain)

| Table                    | Rows    | Time Range | MUST Filter By                                        |
| ------------------------ | ------- | ---------- | ----------------------------------------------------- |
| `agent.bsc_dex_trades`   | ~4.0B   | 2020-09+   | `block_time` (PK) or `block_date` (partition)         |
| `agent.bsc_transactions` | ~12.1B  | 2020-09+   | `block_date` (partition)                              |
| `agent.bsc_traces`       | ~117.8B | 2020-09+   | `block_date` (partition) + `transaction_hash` (bloom) |
| `agent.bsc_event_logs`   | ~46.2B  | 2020-09+   | `block_date` (partition) + `address` (PK)             |
| `agent.bsc_transfers`    | large   | 2020-09+   | `contract_address` (PK) + `block_date` (partition)    |

#### Tron

| Table                     | Rows  | Time Range | MUST Filter By                                        |
| ------------------------- | ----- | ---------- | ----------------------------------------------------- |
| `agent.tron_dex_trades`   | large | 2019+      | `block_time` (PK) or `block_date` (partition)         |
| `agent.tron_transactions` | large | 2018+      | `block_date` (partition)                              |
| `agent.tron_blocks`       | large | 2018+      | `date` or `number`                                    |
| `agent.tron_event_logs`   | large | 2018+      | `block_date` (partition) + `address` (PK)             |
| `agent.tron_transfers`    | large | 2018+      | `contract_address` (PK) + `block_date` (partition)    |
| `agent.tron_tvl_daily`    | small | 2020+      | `block_date` + `project` (small, safe to scan)        |

#### Bitcoin

| Table                        | Rows   | Time Range | MUST Filter By                        |
| ---------------------------- | ------ | ---------- | ------------------------------------- |
| `agent.bitcoin_blocks`       | ~943K  | genesis+   | `date` or `height`                    |
| `agent.bitcoin_transactions` | ~1.3B  | genesis+   | `block_date` + `block_height`         |
| `agent.bitcoin_inputs`       | large  | genesis+   | `block_date` + `tx_id`               |
| `agent.bitcoin_outputs`      | large  | genesis+   | `block_date` + `tx_id`               |

#### HyperEVM

| Table                            | Rows   | Time Range | MUST Filter By                                    |
| -------------------------------- | ------ | ---------- | ------------------------------------------------- |
| `agent.hyperevm_blocks`          | ~30.7M | 2024+      | `date` or `number`                                |
| `agent.hyperevm_dex_base_trades` | ~71.1M | 2024+      | `block_time` (PK) or `block_date` (partition)     |
| `agent.hyperevm_event_logs`      | ~483M  | 2024+      | `block_date` + `contract_address`                 |
| `agent.hyperevm_transactions`    | ~127M  | 2024+      | `block_date` (partition)                           |

#### Bridge Volume

| Table                       | Rows  | Time Range | MUST Filter By                                          |
| --------------------------- | ----- | ---------- | ------------------------------------------------------- |
| `agent.bridge_volume_daily` | ~16K  | 2020+      | `block_date` + `project` (small, safe to scan)          |

#### DeFi Yields (Ethereum)

`agent.ethereum_yields_daily` (~11.4M rows) — daily yield/APY data per pool.

Key columns: `project`, `pool_address`, `symbol`, `apy`, `apy_base`, `apy_reward`, `tvl_usd`, `total_supply_usd`, `total_borrow_usd`, `stablecoin`, `exposure`, `il_risk`.

Filter by: `block_date` + `project` (or `pool_address`).

#### Hyperliquid Perpetuals

| Table                             | Rows   | Time Range | MUST Filter By                                 |
| --------------------------------- | ------ | ---------- | ---------------------------------------------- |
| `agent.hyperliquid_funding_rates` | ~3.7M  | 2023-05+   | `funding_date` + `coin`                        |
| `agent.hyperliquid_market_data`   | ~101K  | recent     | `snapshot_date` + `coin` (small, safe to scan) |
| `agent.hyperliquid_perp_meta`     | ~229   | snapshot   | None (tiny reference table)                    |

#### Prediction Markets — Polymarket

| Table                                       | Rows    | Time Range | MUST Filter By                                 |
| ------------------------------------------- | ------- | ---------- | ---------------------------------------------- |
| `agent.polymarket_market_details`           | ~1.5M   | 2020-10+   | `condition_id` (PK) or scan (small)            |
| `agent.polymarket_market_prices_hourly`     | ~33.5M  | 2022-11+   | `block_hour` + `condition_id`                  |
| `agent.polymarket_market_prices_latest`     | ~1.2M   | 2022-12+   | scan (small)                                   |
| `agent.polymarket_market_prices_daily`      | ~5.8M   | 2022-11+   | `block_date` (partition) + `condition_id` (PK) |
| `agent.polymarket_market_trades`            | ~963M   | 2022-11+   | `block_date` (partition) or `block_time` (PK)  |
| `agent.polymarket_market_volume_daily`      | ~3.1M   | 2022-11+   | `block_date` + `condition_id`                  |
| `agent.polymarket_market_volume_hourly`     | ~18.5M  | 2022-11+   | `block_hour` + `condition_id`                  |
| `agent.polymarket_positions`                | large   | 2020-10+   | `day` (MUST!) + `condition_id`                 |
| `agent.polymarket_market_category`          | ~725K   | —          | `condition_id` or scan (small)                 |
| `agent.polymarket_market_ranking`           | ~725K   | —          | `condition_id` or scan (small)                 |
| `agent.polymarket_market_report`            | ~71.6M  | 2020+      | `date` (MUST!) + `condition_id`                |
| `agent.polymarket_leaderboard`              | small   | snapshot   | scan (small)                                   |
| `agent.polymarket_leaderboard_daily`        | ~2.4M   | 2020+      | `address` or scan                              |
| `agent.polymarket_leaderboard_monthly`      | ~2.4M   | 2020+      | `address` or scan                              |
| `agent.polymarket_leaderboard_weekly`       | ~2.4M   | 2020+      | `address` or scan                              |
| `agent.polymarket_user_activity_api`        | ~1.1B   | 2020+      | `block_time` + `proxy_wallet` (MUST!)          |
| `agent.polymarket_user_positions`           | large   | 2020+      | `address` + `condition_id`                     |
| `agent.polymarket_user_positions_api`       | large   | 2020+      | `address` + `condition_id`                     |

#### Prediction Markets — Kalshi

| Table                                | Rows   | Time Range | MUST Filter By                           |
| ------------------------------------ | ------ | ---------- | ---------------------------------------- |
| `agent.kalshi_market_details`        | ~58.7M | 2021-06+   | `market_ticker` (PK) or scan             |
| `agent.kalshi_market_report`         | ~17.3M | 2021-06+   | `date` (MUST!)                           |
| `agent.kalshi_trades`                | ~317M  | 2021-06+   | `trade_date` (MUST!)                     |
| `agent.kalshi_market_prices_daily`   | small  | 2021-06+   | `block_date` + `ticker`                  |
| `agent.kalshi_market_prices_hourly`  | small  | 2021-06+   | `block_hour` + `ticker`                  |
| `agent.prediction_markets_daily`     | ~189K  | 2020-09+   | `date` + `source` (small, safe to scan)  |

#### Tempo Network

| Table                                | Rows  | Time Range | MUST Filter By                              |
| ------------------------------------ | ----- | ---------- | ------------------------------------------- |
| `agent.tempo_transfers`              | ~2.8M | recent     | `block_date` + `token_address`              |
| `agent.tempo_transfer_with_memo`     | ~66K  | recent     | `block_date`                                |
| `agent.tempo_bridge_flows`           | ~94   | recent     | scan (tiny)                                 |
| `agent.tempo_contract_calls_daily`   | ~8.7K | recent     | `block_date` + `contract_address` (small)   |
| `agent.tempo_contract_deployments`   | ~11K  | recent     | `block_date` (small)                        |
| `agent.tempo_dex_swaps`             | ~13K  | recent     | `block_date` (small)                        |
| `agent.tempo_dex_trades_daily`       | ~24   | recent     | scan (tiny)                                 |
| `agent.tempo_metrics`                | ~3    | recent     | scan (tiny, daily chain-level stats)        |
| `agent.tempo_token_metrics`          | ~47   | recent     | scan (tiny)                                 |
| `agent.tempo_internal_transfers`     | 0     | —          | empty                                       |

#### x402 Payments (Base)

| Table                           | Rows  | Time Range | MUST Filter By                          |
| ------------------------------- | ----- | ---------- | --------------------------------------- |
| `agent.x402_base_payments`      | ~684K | 2024+      | `block_date` + `facilitator`            |
| `agent.x402_base_payments_daily`| ~275  | 2024+      | `block_date` (small, safe to scan)      |

### SQL Validation Rules

- **Read-only**: Only `SELECT` and `WITH` allowed
- **Single statement**: No `;` separated multi-statements
- **Row limit**: Results capped at 10,000 rows
- **Row read limit**: Queries scanning >5B rows are killed
- **Timeout**: 30 seconds max

### SQL Dialect Quick Reference

```sql
-- Date functions
today()                          -- Current date
today() - 7                      -- 7 days ago
today() - INTERVAL 1 MONTH      -- 1 month ago
toStartOfDay(block_time)         -- Truncate to day
toStartOfHour(block_time)        -- Truncate to hour
toStartOfWeek(block_date)        -- Truncate to week (Monday)
toYear(block_date)               -- Extract year
toMonth(block_date)              -- Extract month (1-12)
toHour(block_time)               -- Extract hour (0-23)
formatDateTime(block_time, '%Y-%m-%d %H:%M:%S')

-- Type conversion
toFloat64(value) / 1e18          -- Wei to ETH
gas_price / 1e9                  -- Wei to Gwei
toDecimal64(value, 18)           -- High-precision decimal
toDate('2024-01-01')             -- Parse date string

-- Aggregation
SUM(x), AVG(x), COUNT(*), MIN(x), MAX(x)
argMax(tx_hash, amount_usd)      -- tx_hash with max amount_usd
quantile(0.5)(amount_usd)        -- Median
quantile(0.95)(amount_usd)       -- 95th percentile

-- IMPORTANT: Use approximate count on large tables (10-100x faster, <1% error)
uniqHLL12(taker)                 -- Instead of COUNT(DISTINCT taker)

-- Array (1-indexed)
topics[1]                        -- Event signature hash
has(topics, '0xddf252ad...')     -- Check contains
arrayJoin([1, 2, 3])            -- Expand to rows
groupArray(token_pair)           -- Collect into array

-- String
LIKE '%pattern%'
startsWith(ticker, 'KXBTC')
lower(address), upper(symbol)
hex(value), unhex(data)

-- NULL handling
WHERE amount_usd IS NOT NULL
COALESCE(amount_usd, 0)
ifNull(amount_usd, 0)

-- Reserved words (transfers tables)
SELECT `from`, `to`, amount_raw FROM agent.ethereum_transfers
```

## ClickHouse → JSON Type Mapping

Values in the `data` array returned by `/onchain/sql` depend on the ClickHouse column type. **You MUST handle them according to this table:**

| ClickHouse Type | JSON Type | Frontend Handling | Notes |
|---|---|---|---|
| String, UUID | string | Use directly | — |
| UInt8/16/32/64, Int8/16/32/64 | number | Use directly | — |
| Float32/64 | number | Use directly | Possible floating-point precision issues |
| Boolean | boolean | Use directly | — |
| **DateTime / DateTime64** | **number (Unix seconds)** | `new Date(val * 1000)` | **NOT an ISO string — must multiply by 1000** |
| **Date** | **number (Unix seconds)** | `new Date(val * 1000)` | Same as above |
| **UInt256 / Int256** | **string** | Keep as string, use `BigInt()` | **Never use `Number()` — precision loss** |
| **Decimal(P,S)** | **string** | Keep as string | No decimal point info; you need to know the scale |
| **Nullable(T)** | T's type \| null | Must null-check: `if (val !== null)` | — |
| **Array(T)** | string (structure lost) | Avoid, or unpack via subquery | Serialized via `fmt.Sprintf` — not parseable |

### Common Pitfalls

1. `block_time: 1710892800` — This is Unix **seconds**, not milliseconds. `new Date(1710892800)` gives a date in 1970
2. `amount_raw: "1000000000000000000"` — This is a **string**, not a number. `Number("1000000000000000000")` loses precision
3. `amount_usd: null` — Nullable fields can be null. Calling `.toFixed(2)` on null will crash
4. Avoid `SELECT *` on tables with Array columns — Arrays are serialized to unparseable strings

**Tip:** Format date/time in SQL directly to avoid client-side conversion:

```sql
SELECT formatDateTime(toDateTime(funding_date), '%Y-%m-%d') as date_str
```

### Schema Discovery

**Before writing SQL, always query the schema endpoint to get column names and types.** Do NOT embed schema-fetching in production rendering logic — use it at dev time to inform your query.

```bash
# Via curl (backend/sandbox)
curl -s "$DATA_PROXY_BASE/onchain/schema" | jq '.data[] | select(.table=="ethereum_dex_trades") | .columns[] | {name, type}'

# Via SDK (backend route)
# const schema = await dataApi.onchain.schema()
# Returns: { data: [{ database, table, columns: [{ name, type, comment? }] }] }
```

### Frontend Data Safety — CRITICAL

**Onchain SQL returns dynamic, loosely-typed data (`Record<string, any>[]`). You MUST write defensive frontend code to prevent runtime errors from crashing the page via the error boundary.**

#### Rules

1. **Always use optional chaining on query results**:

   ```ts
   // BAD — crashes if data is undefined or row is missing field
   data.data.map((row) => row.amount_usd.toFixed(2));

   // GOOD — Number() coerces null/string/undefined safely
   (data?.data ?? []).map((row) => Number(row.amount_usd ?? 0).toFixed(2));
   ```

2. **Default empty arrays for `.map()` / `.forEach()` / `.reduce()`**:

   ```ts
   // BAD — "Cannot read properties of undefined (reading 'map')"
   data.data.map(...)

   // GOOD
   (data?.data ?? []).map(...)
   ```

3. **Guard number operations — values may be `null`, `string`, or `undefined`**:

   ```ts
   // BAD — NaN propagation or .toFixed crash
   row.amount_usd.toFixed(2);

   // GOOD
   Number(row.amount_usd ?? 0).toFixed(2);
   ```

4. **Guard string operations — `Date`/numeric columns are NOT strings**:

   ```ts
   // BAD — epoch seconds are integers, .slice() crashes
   row.block_date.slice(0, 10);

   // GOOD — convert first
   new Date((row.block_date ?? 0) * 1000).toISOString().slice(0, 10);
   ```

5. **Handle empty results gracefully** — queries may return 0 rows:

   ```tsx
   {(data?.data?.length ?? 0) === 0 ? (
     <EmptyState message="No data found for this period" />
   ) : (
     <Table data={data.data} ... />
   )}
   ```

6. **Wrap data-heavy components with per-section error boundaries**:

   ```tsx
   // Don't let one broken chart crash the whole dashboard
   <ErrorBoundary fallback={<div>Failed to load chart</div>}>
     <VolumeChart data={data?.data ?? []} />
   </ErrorBoundary>
   ```

7. **Type-narrow before rendering** — ClickHouse `Nullable` columns return `null`:

   ```ts
   // BAD — null renders as empty but crashes in operations
   <span>{row.token_bought_symbol}</span>  // ok to render
   <span>{row.token_bought_symbol.toUpperCase()}</span>  // crashes on null!

   // GOOD
   <span>{row.token_bought_symbol?.toUpperCase() ?? 'N/A'}</span>
   ```

### Best Practices

- **Query schema endpoint first** — always run `curl "$DATA_PROXY_BASE/onchain/schema"` to get column names/types before writing SQL
- **Always filter by indexed columns** — see "MUST Filter By" in Table Index. Wrong filters on billion-row tables cause timeouts
- **Keep time ranges short** — 7 days safe, 30 days OK, 365 days on large tables risks timeout
- **Use `uniqHLL12()`** over `COUNT(DISTINCT ...)` — 10-100x faster, <1% error
- **Avoid `SELECT *`** — only select needed columns; `input` and `data` blobs are large
- **Always add `LIMIT`** — max 10,000 rows
- **Avoid cross-table JOINs** — ClickHouse JOIN performance is poor on large tables. Query separately and combine in code
- **Transfers: use `block_date` NOT `block_time`** for time filtering — `block_time` won't hit partition key
- **Data has ~1-2 day lag** — use `today() - 3` instead of `today() - 1` to avoid empty results
- **BSC tables are massive** — bsc_traces (~118B), bsc_event_logs (~46B), bsc_transactions (~12B). Always use tight date ranges
- **Polymarket/Kalshi details and category tables** are small enough to scan without time filters
- **polymarket_market_trades (~963M rows)** — always filter by `block_date` or `block_time`
- **polymarket_user_activity_api (~1.1B rows)** — always filter by `block_time` + `proxy_wallet`
- **polymarket_positions** — always filter by `day`
- **kalshi_trades (~317M rows)** — always filter by `trade_date`
- **kalshi_market_report** — always filter by `date`
- **prediction_markets_daily** — small cross-platform summary, great for platform-level comparisons
- **Bitcoin tables** — use UTXO model: `bitcoin_inputs` + `bitcoin_outputs` for value flow; filter by `block_date` + `tx_id`
- **Tempo tables** — mostly small (new chain), safe to scan; `tempo_transfers` (~2.8M) filter by `block_date`

## SQL Pre-Validation (Mandatory)

**Before embedding any SQL query into a frontend component, you MUST validate it first:**

1. Call `dataApi.onchain.sql({ sql: '...', max_rows: 5 })` or `curl /proxy/onchain/sql` with minimal rows for validation
2. Check the response status:
   - 400 → SQL syntax or column error — fix based on the error message
   - 502 → ClickHouse unavailable — fall back to another data source
   - 200 → proceed to next step
3. Inspect the returned data:
   - Confirm column names match expectations
   - Confirm value types match the type mapping table above
   - Confirm non-empty data (empty results = filters too strict or table has no data for that range)
4. Check response time:
   - < 3s: use normally
   - 3–10s: must add a loading state
   - > 10s: optimize the SQL (narrow time range, add partition filter, reduce aggregations)
5. Only after validation passes, write the SQL into the component code

**Never embed unvalidated SQL into components.**
