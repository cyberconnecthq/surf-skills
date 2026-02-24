---
name: surf-data-clickhouse
description: Query ClickHouse Cloud databases for blockchain data (surf) and product analytics (surf-analytics). Use when exploring on-chain data (transactions, DEX trades, prices, tokens, lending, bridges), user analytics, chat sessions, langfuse traces, or posthog events.
---

# ClickHouse Query Skill

All paths below are relative to this skill's base directory. Resolve to absolute paths before executing.

Query two internally hosted ClickHouse instances via read-only access. The script auto-detects whether it's running inside the k8s cluster (uses HTTP:8123) or externally (uses HTTPS:8443).

## First-Time Setup Check

Before running queries, verify the script can reach AWS Secrets Manager:

```bash
scripts/ch-query --check-setup
```

Requirements:
- AWS CLI configured with access to Secrets Manager in `us-west-2`
- `curl` installed (used for ClickHouse HTTP API)
- `jq` installed (used to parse AWS secrets)

## Instances

| Instance | Secret ID | Public Host | Internal Host (k8s) | Purpose |
|----------|-----------|-------------|---------------------|---------|
| `surf` | `clickhouse/surf/bot_ro` | `clickhouse.ask.surf` | `clickhouse-clickhouse.clickhouse.svc.cluster.local` | Blockchain data: Ethereum transactions, DEX trades, prices, tokens, lending protocols, bridges |
| `surf-analytics` | `clickhouse/surf-analytics/bot_ro` | `surf-analytics-clickhouse.ask.surf` | `clickhouse-surf-analytics.clickhouse.svc.cluster.local` | Product analytics: users, chat sessions, messages, langfuse traces, posthog events, subscriptions |

**Network auto-detection**: The script checks `KUBERNETES_SERVICE_HOST` to detect if it's running inside a k8s pod. If yes, it uses the internal host via HTTP:8123. Otherwise, it uses the public host via HTTPS:8443.

## Available Commands

Script: `scripts/ch-query`

### Query

```bash
# Query surf (blockchain data)
scripts/ch-query --instance surf --sql "SELECT * FROM ethereum.transactions LIMIT 10"

# Query surf-analytics (product data)
scripts/ch-query --instance analytics --sql "SELECT count() FROM default.users"

# With specific database
scripts/ch-query --instance surf --db prices --sql "SELECT * FROM prices_coingecko_hour WHERE symbol = 'ETH' ORDER BY hour DESC LIMIT 10"

# Output formats
scripts/ch-query --instance analytics --sql "SELECT ..." --format TSV
scripts/ch-query --instance analytics --sql "SELECT ..." --format JSON
scripts/ch-query --instance analytics --sql "SELECT ..." --format CSV
```

### Explore Schema

```bash
# List databases
scripts/ch-query --instance surf --sql "SHOW DATABASES"

# List tables in a database
scripts/ch-query --instance surf --db ethereum --sql "SHOW TABLES"

# Describe table
scripts/ch-query --instance surf --sql "DESCRIBE TABLE ethereum.transactions"

# Table sizes
scripts/ch-query --instance analytics --sql "SELECT name, total_rows, formatReadableSize(total_bytes) as size FROM system.tables WHERE database = 'default' ORDER BY total_rows DESC"
```

## Safety Rules

- **Read-only**: The read-only `bot_ro` user only has SELECT/SHOW access. Write operations will be rejected by ClickHouse.
- **No credentials in chat**: Never display passwords or secret values. The script fetches them from AWS Secrets Manager at runtime.
- **Large queries**: Always use `LIMIT` when exploring data. Some tables have billions of rows.
- **Large scans**: Avoid `SELECT *` on large tables without filters. Use LIMIT and WHERE clauses.

## Common Query Patterns

Before writing queries, read the reference docs for table schemas:
- **Blockchain data (surf)**: Read `references/surf-tables.md`
- **Product analytics (surf-analytics)**: Read `references/analytics-tables.md`

### Blockchain Examples

```sql
-- Recent ETH transactions for an address
SELECT block_timestamp, transaction_hash, from_address, to_address, value / 1e18 as eth_value
FROM ethereum.transactions
WHERE from_address = '0x...' OR to_address = '0x...'
ORDER BY block_timestamp DESC LIMIT 20

-- Token price history
SELECT hour, symbol, price FROM prices.prices_coingecko_hour
WHERE symbol = 'ETH' AND hour >= now() - INTERVAL 7 DAY
ORDER BY hour DESC

-- ERC20 token info
SELECT * FROM tokens.erc20 WHERE symbol = 'USDC'
```

### Product Analytics Examples

```sql
-- Daily active users (last 30 days)
SELECT toDate(created_at) as day, uniqExact(user_id) as dau
FROM default.chat_messages
WHERE created_at >= now() - INTERVAL 30 DAY
GROUP BY day ORDER BY day DESC

-- User lookup (IMPORTANT: email is often NULL, search all email fields)
SELECT id, name, email, google_email, apple_email, created_at, last_login_at
FROM default.users
WHERE email ILIKE '%query%' OR google_email ILIKE '%query%' OR apple_email ILIKE '%query%'

-- Referral analysis for a user
SELECT
    countIf(invited_user_id IS NOT NULL) as successful_referrals,
    countIf(invited_user_id IN (
        SELECT user_id FROM default.user_subscriptions
        WHERE payment_source != 'FREE' AND subscription_type != 'PRO_TRIAL'
    )) as converted_to_paying
FROM default.invitation_codes
WHERE owner_user_id = 'uuid-here'

-- Session messages
SELECT id, human_message, status, created_at
FROM default.chat_messages
WHERE session_id = 'uuid-here'
ORDER BY created_at
```

## ClickHouse Query Gotchas

These are hard-won lessons from production analytics work:

### CTE column names collide with output aliases
ClickHouse throws `ILLEGAL_AGGREGATION` when a CTE column name matches an outer `countIf`/`sumIf` alias. For example, a CTE column named `registered` will collide with `countIf(...) AS registered` in the outer SELECT. **Fix**: prefix CTE columns with `did_` (e.g., `did_register`, `did_visit`, `did_pay`).

### CTE + LEFT JOIN produces false 100% matches
ClickHouse CTEs used in `LEFT JOIN` can materialize incorrectly, producing false matches (e.g., 100/100 instead of 5/100). This is a known ClickHouse materialization issue. **Fix**: replace `LEFT JOIN cte ON ...` with `IN (SELECT ... FROM cte)` subquery.

### PostHog person_id is NOT the app user ID
`posthog_events.person_id` is PostHog's internal identifier. It does **not** equal `users.id`. To get the app user ID for joins to `users`/`invoices`/etc., use `argMax(distinct_id, timestamp)` grouped by `coalesce(person_id, distinct_id)`. See `references/analytics-tables.md` for the full pattern.

### PostHog distinct_id merging collapses funnels
After identification, PostHog batch exports merge all `distinct_id` values, so `COUNT DISTINCT` on visitors/registered/paid returns the same number. Use flag-based per-person aggregation instead. See `references/analytics-tables.md` for the correct funnel pattern.

### Always verify SQL against live ClickHouse
Mocked unit tests don't catch ClickHouse-specific syntax errors (FINAL alias ordering, CTE materialization bugs, aggregate alias collisions). Always test queries against the real database.

## Query Performance Best Practices

### Check table ORDER BY before writing WHERE clauses
ClickHouse can only use primary key index pruning if your WHERE filters match the **leftmost prefix** of the ORDER BY key. Check the table's ORDER BY with `SHOW CREATE TABLE` and filter on those columns first.
```sql
-- Table: ORDER BY (project_id, type, toDate(start_time), id)
-- GOOD: filters on leftmost keys → granule pruning
WHERE project_id = 'xxx' AND type = 'GENERATION' AND toDate(start_time) >= today() - 7
-- BAD: skips project_id and type → full scan
WHERE start_time >= now() - INTERVAL 7 DAY
```

### Use partition filters for time-range queries
Tables with `PARTITION BY toYYYYMM(timestamp)` can skip entire months of data. Always include a time filter that aligns with the partition key so ClickHouse prunes partitions before reading.
```sql
-- Table: PARTITION BY toYYYYMM(created_at)
-- GOOD: ClickHouse only reads 1 partition
WHERE created_at >= now() - INTERVAL 2 DAY
-- BAD: no time filter → scans all partitions
WHERE user_id = 'xxx'
```

### Don't wrap ORDER BY columns in functions
Wrapping a primary key column in a function prevents index usage. Move the function to the other side of the comparison.
```sql
-- BAD: toString() wraps the ORDER BY key → no index
WHERE toString(user_id) = 'some-uuid'
-- GOOD: direct comparison → index works
WHERE user_id = toUUID('some-uuid')

-- BAD: toDate() on indexed column
WHERE toDate(created_at) = today()
-- GOOD: range comparison preserves index
WHERE created_at >= today() AND created_at < today() + 1
```

### Use bloom_filter indexes for point lookups on non-primary columns
Tables may have `bloom_filter` secondary indexes on columns like `session_id`, `trace_id`, `user_id`. These allow fast point lookups even when the column isn't in the ORDER BY. Check with:
```sql
SELECT table, name, expr FROM system.data_skipping_indices WHERE database = 'your_db'
```

### Scope subqueries and anti-joins
Unbounded subqueries in `NOT IN` or `IN` clauses scan entire tables. Always add a time filter inside the subquery.
```sql
-- BAD: full table scan of response_eval_scores
WHERE id NOT IN (SELECT observation_id FROM response_eval_scores FINAL)
-- GOOD: scoped to recent data
WHERE id NOT IN (SELECT observation_id FROM response_eval_scores FINAL WHERE evaluated_at >= now() - INTERVAL 3 DAY)
```

### Avoid reading large String columns unnecessarily
Columns like `input`, `output`, `metadata` can be huge (multi-KB per row). Don't use `length(input) > 0` to check non-emptiness — it forces reading the entire column from S3 storage. Use `IS NOT NULL` instead (reads only the null bitmap).

## Error Handling

If queries fail:
1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify secret exists: `aws secretsmanager get-secret-value --region us-west-2 --secret-id clickhouse/surf/bot_ro --query SecretString --output text | jq .public_host`
3. Run setup check: `scripts/ch-query --check-setup` (shows which host/port is selected and connectivity status)
