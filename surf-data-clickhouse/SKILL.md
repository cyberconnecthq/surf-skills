---
name: surf-data-clickhouse
description: Query ClickHouse Cloud databases for blockchain data (surf) and product analytics (surf-analytics). Use when exploring on-chain data (transactions, DEX trades, prices, tokens, lending, bridges), user analytics, chat sessions, langfuse traces, or posthog events.
---

# ClickHouse Query Skill

All paths below are relative to this skill's base directory. Resolve to absolute paths before executing.

Query two ClickHouse Cloud instances via read-only access.

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

| Instance | Secret ID | Purpose |
|----------|-----------|---------|
| `surf` | `clickhouse/surf/bot_ro` | Blockchain data: Ethereum transactions, DEX trades, prices, tokens, lending protocols, bridges |
| `surf-analytics` | `clickhouse/surf-analytics/bot_ro` | Product analytics: users, chat sessions, messages, langfuse traces, posthog events, subscriptions |

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

- **Read-only**: The `bot_ro` user only has SELECT access. Write operations will be rejected by ClickHouse.
- **No credentials in chat**: Never display passwords or secret values. The script fetches them from AWS Secrets Manager at runtime.
- **Large queries**: Always use `LIMIT` when exploring data. Some tables have billions of rows.
- **Cost awareness**: ClickHouse Cloud charges by compute. Avoid `SELECT *` on large tables without filters.

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

## Error Handling

If queries fail:
1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify secret exists: `aws secretsmanager get-secret-value --region us-west-2 --secret-id clickhouse/surf/bot_ro --query SecretString --output text | jq .host`
3. Test connectivity: the script will show the HTTP status code on failure
