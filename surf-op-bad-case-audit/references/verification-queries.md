# Verification Queries

ClickHouse SQL queries for fact-checking AI claims. All queries use the `surf-data-clickhouse` skill's `ch-query` script.

**Instance:** `surf` for price/blockchain data, `analytics` for user/session data.

---

## Price Verification

### Current/recent price

```sql
-- Verify price at a specific time
-- Instance: surf
SELECT
    hour,
    symbol,
    price,
    volume
FROM external.coingecko_hour
WHERE symbol = '{TOKEN}'
  AND hour >= toDateTime('{DATE} 00:00:00')
  AND hour <= toDateTime('{DATE} 23:59:59')
ORDER BY hour DESC
LIMIT 10
```

### All-time high / all-time low

```sql
-- Find ATH and ATL per year
-- Instance: surf
SELECT
    toYear(hour) as year,
    max(price) as ath,
    argMax(toDate(hour), price) as ath_date,
    min(price) as atl,
    argMin(toDate(hour), price) as atl_date,
    avg(price) as avg_price
FROM external.coingecko_hour
WHERE symbol = '{TOKEN}'
  AND price > 0
GROUP BY year
ORDER BY year DESC
```

### Token ratio over time (e.g., SOL/BTC)

```sql
-- Calculate ratio between two tokens
-- Instance: surf
SELECT
    toYear(a.hour) as year,
    avg(a.price / b.price) as avg_ratio,
    max(a.price / b.price) as peak_ratio,
    argMax(toDate(a.hour), a.price / b.price) as peak_date,
    min(a.price / b.price) as trough_ratio,
    argMin(toDate(a.hour), a.price / b.price) as trough_date
FROM external.coingecko_hour a
JOIN external.coingecko_hour b
    ON a.hour = b.hour AND b.symbol = 'BTC'
WHERE a.symbol = '{TOKEN}'
  AND a.price > 0 AND b.price > 0
GROUP BY year
ORDER BY year
```

### Price on a specific date (for event correlation)

```sql
-- What was the price when an event happened?
-- Instance: surf
SELECT
    hour,
    symbol,
    price
FROM external.coingecko_hour
WHERE symbol = '{TOKEN}'
  AND toDate(hour) = '{DATE}'
ORDER BY hour
LIMIT 24
```

### Market cap derived circulating supply

```sql
-- Derive circulating supply from market cap / price
-- (when supply data isn't directly available)
-- Instance: surf
SELECT
    hour,
    symbol,
    price,
    market_cap,
    if(price > 0, market_cap / price, 0) as derived_supply
FROM external.coingecko_hour
WHERE symbol = '{TOKEN}'
ORDER BY hour DESC
LIMIT 1
```

---

## Session & Feedback Data

### Pull feedback for a time range

```sql
-- Instance: analytics
SELECT
    f.id,
    f.user_id,
    f.session_id,
    f.content,
    f.type,
    f.created_at
FROM default.feedbacks f
WHERE f.created_at >= now() - INTERVAL {DAYS} DAY
ORDER BY f.created_at DESC
```

### Get chat messages for a session

```sql
-- Instance: analytics
SELECT
    cm.id,
    cm.session_id,
    cm.human_message,
    cm.ai_massage,
    cm.user_goal,
    cm.core_subject,
    cm.ai_action,
    cm.surf_platform,
    cm.lang,
    cm.created_at
FROM default.chat_messages cm
WHERE cm.session_id = '{SESSION_ID}'
ORDER BY cm.created_at
```

### Get Langfuse traces for a session

```sql
-- Instance: analytics
SELECT
    lt.id as trace_id,
    lt.name,
    lt.session_id,
    lt.timestamp,
    lt.tags,
    length(lt.input) as input_len,
    length(lt.output) as output_len
FROM default.langfuse_traces lt
WHERE lt.session_id = '{SESSION_ID}'
ORDER BY lt.timestamp
```

### Get message interactions (thumbs up/down)

```sql
-- Instance: analytics
SELECT
    mi.id,
    mi.user_id,
    mi.session_id,
    mi.message_id,
    mi.type,
    mi.content,
    mi.created_at
FROM default.message_interactions mi
WHERE mi.created_at >= now() - INTERVAL {DAYS} DAY
ORDER BY mi.created_at DESC
```

---

## Feedback Trend Analysis

### Weekly feedback volume

```sql
-- Instance: analytics
SELECT
    toStartOfWeek(created_at) as week,
    count() as total,
    countIf(type = 'thumbs_down') as thumbs_down,
    countIf(type = 'feedback') as text_feedback
FROM default.feedbacks
WHERE created_at >= now() - INTERVAL 28 DAY
GROUP BY week
ORDER BY week DESC
```

### Top complained-about topics

```sql
-- Instance: analytics
SELECT
    cm.core_subject,
    count() as complaint_count
FROM default.feedbacks f
JOIN default.chat_messages cm
    ON f.session_id = cm.session_id
WHERE f.created_at >= now() - INTERVAL 7 DAY
GROUP BY cm.core_subject
ORDER BY complaint_count DESC
LIMIT 20
```

### Feedback by platform

```sql
-- Instance: analytics
SELECT
    cm.surf_platform,
    count() as complaint_count
FROM default.feedbacks f
JOIN default.chat_messages cm
    ON f.session_id = cm.session_id
WHERE f.created_at >= now() - INTERVAL 7 DAY
GROUP BY cm.surf_platform
ORDER BY complaint_count DESC
```

---

## ETH-Specific Verification

### ETH price from prices_ethereum

```sql
-- Alternative ETH price source (use if coingecko_hour is missing data)
-- Instance: surf, DB: prices_ethereum
SELECT
    hour,
    price_eth_usd
FROM prices_ethereum.combined_hour
WHERE hour >= toDateTime('{DATE} 00:00:00')
  AND hour <= toDateTime('{DATE} 23:59:59')
ORDER BY hour DESC
LIMIT 10
```

> **Note:** `prices_ethereum.combined_hour` contains wrapped BTC tokens with misleading prices. Always filter by `price_eth_usd` column, not generic price columns.

---

## Important Notes

### Table: `external.coingecko_hour`
- **Instance:** `surf`
- **Size:** ~22.6M rows
- **Coverage:** Most major tokens, hourly VWAP prices from CoinGecko
- **Columns:** `hour`, `symbol`, `price`, `volume`, `market_cap`
- **Use for:** Price verification, ATH checks, ratio calculations

### Table: `default.feedbacks`
- **Instance:** `analytics`
- **Size:** ~970 rows (small but growing)
- **Use for:** Pulling user complaints

### Table: `default.chat_messages`
- **Instance:** `analytics`
- **Column typo:** AI response is in `ai_massage` (not `ai_message`)
- **Use for:** Getting the full conversation context

### Table: `default.langfuse_traces`
- **Instance:** `analytics`
- **Size:** ~7.6M rows
- **Use for:** Matching sessions to traces for tool-level analysis

---

## Eval Pipeline Data

### Check eval results for a trace

```sql
-- Instance: analytics
SELECT
    observation_id,
    trace_id,
    faithfulness_score,
    relevance_score,
    completeness_score,
    has_hallucination,
    has_contradiction,
    failure_category,
    failure_detail,
    tool_usage_pass,
    tool_usage_detail
FROM default.response_eval_scores
WHERE trace_id = '{TRACE_ID}'
```

### Check sentiment for a message

```sql
-- Instance: analytics
SELECT
    message_id,
    sentiment,
    confidence,
    severity,
    reasoning,
    evaluated_at
FROM default.message_sentiments
WHERE message_id = '{MESSAGE_ID}'
```

### Cross-reference confirmed failures (sentiment + eval)

```sql
-- Instance: analytics
-- Direct join via message_id
SELECT
    e.observation_id,
    e.trace_id,
    e.faithfulness_score,
    e.failure_category,
    s.sentiment,
    s.severity,
    s.reasoning as user_complaint
FROM default.response_eval_scores e
JOIN default.message_sentiments s
    ON e.message_id = s.message_id
WHERE s.sentiment IN ('inaccuracy_complaint', 'correction', 'frustration', 'doubt_uncertainty')
  AND e.faithfulness_score < 0.5
ORDER BY e.faithfulness_score ASC
```

### Session-based cross-reference (more coverage)

```sql
-- Instance: analytics
-- When message_id join yields few results, use session_id via langfuse_traces
SELECT
    e.observation_id,
    e.trace_id,
    e.faithfulness_score,
    e.failure_category,
    s.sentiment,
    s.severity,
    s.human_message
FROM default.response_eval_scores e
JOIN default.langfuse_traces lt ON e.trace_id = lt.id
JOIN default.message_sentiments s ON lt.session_id = s.session_id
WHERE s.sentiment IN ('inaccuracy_complaint', 'correction', 'frustration', 'doubt_uncertainty')
  AND e.faithfulness_score < 0.5
ORDER BY e.faithfulness_score ASC
```

### Daily eval digest

```sql
-- Instance: analytics
SELECT
    date,
    total_evaluated,
    avg_faithfulness,
    hallucination_rate,
    contradiction_rate,
    confirmed_failures,
    failure_distribution
FROM default.eval_daily_digest
ORDER BY date DESC
LIMIT 30
```

### Worst observations (for deep-dive prioritization)

```sql
-- Instance: analytics
SELECT
    observation_id,
    trace_id,
    faithfulness_score,
    relevance_score,
    completeness_score,
    failure_category,
    has_hallucination,
    substring(failure_detail, 1, 200) as detail
FROM default.response_eval_scores
WHERE faithfulness_score < 0.3
  AND has_hallucination = 1
ORDER BY faithfulness_score ASC
LIMIT 50
```

### Root cause distribution

```sql
-- Instance: analytics
SELECT
    failure_category,
    count() as count,
    round(count() * 100.0 / sum(count()) OVER (), 1) as pct,
    avg(faithfulness_score) as avg_faith
FROM default.response_eval_scores
WHERE failure_category != 'none'
GROUP BY failure_category
ORDER BY count DESC
```

### Tool usage failures

```sql
-- Instance: analytics
SELECT
    observation_id,
    trace_id,
    failure_category,
    tool_usage_detail,
    faithfulness_score
FROM default.response_eval_scores
WHERE tool_usage_pass = 0
ORDER BY faithfulness_score ASC
LIMIT 30
```

### Sentiment distribution

```sql
-- Instance: analytics
SELECT
    sentiment,
    severity,
    count() as count
FROM default.message_sentiments
GROUP BY sentiment, severity
ORDER BY count DESC
```

### False positive analysis

```sql
-- Instance: analytics
-- Check false positive sentiments to tune keyword filter
SELECT
    human_message,
    sentiment,
    confidence,
    reasoning
FROM default.message_sentiments
WHERE sentiment = 'false_positive'
ORDER BY evaluated_at DESC
LIMIT 20
```
