# Surf-Analytics ClickHouse — Product Data

Instance: `surf-analytics` (host resolved from AWS Secrets Manager at runtime)

Three databases:
- **`default`** — Product analytics tables synced from the application database
- **`langfuse_cloud`** — Langfuse cloud S3 export (observations, traces, scores). Replaces the old `default.langfuse_*` tables.
- **`langfuse`** — Self-hosted Langfuse (moving to this as primary; sampled at configurable rate via `LANGFUSE_SECONDARY_SAMPLE_RATE` in odin-flow)

## Tables

### `users` — User accounts (557K rows)

> **IMPORTANT — Email lookup**: The `email` field is usually NULL. Most users sign up via OAuth, so their email is stored in `google_email` or `apple_email` instead. When looking up a user by email, always search ALL email fields:
> ```sql
> SELECT * FROM default.users
> WHERE email ILIKE '%query%' OR google_email ILIKE '%query%' OR apple_email ILIKE '%query%'
> ```

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| name | String | Display name |
| email | Nullable(String) | Often NULL — check google_email/apple_email too |
| avatar_url | String | |
| invitation_code | String | The referrer's code this user entered at signup. Note: for comprehensive referral tracking, use the `invitation_codes` table instead |
| x_id, x_handle, x_display_name | Nullable(String) | Twitter/X profile |
| x_followers_count | Nullable(Int64) | |
| google_id, google_email, google_name | Nullable(String) | Google OAuth — often the real email |
| apple_id, apple_email | Nullable(String) | Apple Sign In — often the real email |
| turnkey_default_eth_address | Nullable(String) | Embedded wallet ETH address |
| turnkey_default_sol_address | Nullable(String) | Embedded wallet SOL address |
| stripe_customer_id | Nullable(String) | Stripe billing |
| platform | Nullable(String) | Signup platform |
| banned | Bool | |
| deleted | Bool | Soft delete |
| created_at | DateTime64(3) | |
| last_login_at | Nullable(DateTime64(3)) | |

### `chat_sessions` — Chat sessions (1.9M rows)
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | |
| user_id | UUID | FK to users |
| title | Nullable(String) | Session title |
| type | Nullable(String) | Session type |
| project_ids | Nullable(String) | Associated projects |
| is_public | Bool | Shared session |
| archived | Bool | |
| campaign | Nullable(String) | Marketing campaign |
| folder_id | Nullable(UUID) | |
| created_at | DateTime64(3) | |

### `chat_messages` — Chat messages (2.8M rows)
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | |
| session_id | UUID | FK to chat_sessions |
| user_id | UUID | FK to users |
| human_message | Nullable(String) | User's message |
| ai_massage | Nullable(String) | AI response (note: typo "massage" in column name) |
| status | LowCardinality(String) | Message status |
| project_id | Nullable(UUID) | |
| session_type | Nullable(String) | |
| user_goal | Nullable(String) | Classified user intent |
| core_subject | Nullable(String) | Classified topic |
| ai_action | Nullable(String) | Classified AI action |
| lang | LowCardinality(Nullable(String)) | Language |
| surf_platform | Nullable(String) | web/ios/android |
| created_at | DateTime64(3) | |

### `langfuse_traces` / `langfuse_observations` / `langfuse_scores` (DEPRECATED)

> **Replaced by `langfuse_cloud.traces`, `langfuse_cloud.observations`, `langfuse_cloud.scores`.**
> Old tables in `default` database will be dropped after migration verification.

---

## `langfuse_cloud` Database — Cloud Langfuse S3 Export

Ingested from S3 JSONL exports via Dagster. Tables use source-matching ORDER BY for efficient queries.

### `langfuse_cloud.traces` — LLM traces (~7.8M rows)

ORDER BY: `(project_id, toDate(timestamp), id)` | PARTITION BY: `toYYYYMM(timestamp)` | Bloom: `idx_id`, `idx_session_id`, `idx_user_id`

| Column | Type | Notes |
|--------|------|-------|
| id | String | Trace ID (hex hash) |
| name | String | Flow name: `AskFast`, `V2_SIMPLE`, `V2_INSTANT`, `V2`, `V2_THINKING`, `Offline Research`, `LangGraph`, `Research` |
| session_id | Nullable(String) | **Join key to `chat_sessions.id`** |
| user_id | String | App user UUID |
| timestamp | DateTime64(3) | |
| environment | LowCardinality(String) | |
| project_id | String | |
| metadata | Map(LowCardinality(String), String) | SDK telemetry only (no `message_id`) |
| tags | Array(String) | |
| input | Nullable(String) | JSON input |
| output | Nullable(String) | JSON output |

### `langfuse_cloud.observations` — LLM observations (~138M rows)

ORDER BY: `(project_id, type, toDate(start_time), id)` | PARTITION BY: `toYYYYMM(start_time)` | Bloom: `idx_id`, `idx_trace_id`

| Column | Type | Notes |
|--------|------|-------|
| id | String | Observation ID |
| trace_id | String | FK to `langfuse_cloud.traces.id` |
| type | LowCardinality(String) | `GENERATION`, `SPAN` |
| name | String | Operation name |
| start_time | DateTime64(3) | |
| end_time | Nullable(DateTime64(3)) | |
| metadata | Map(LowCardinality(String), String) | Contains `message_id`, `user_id`, `thread_id` on root observations |
| provided_model_name | Nullable(String) | LLM model used |
| usage_details | Map(LowCardinality(String), String) | Token counts as strings (`input`, `output`, `total`) |
| cost_details | Map(LowCardinality(String), String) | Cost breakdown as strings (`input`, `output`, `total`) |
| input | Nullable(String) | |
| output | Nullable(String) | |

### `langfuse_cloud.scores` — LLM evaluation scores (~641K rows)

ORDER BY: `(project_id, toDate(timestamp), name, id)` | PARTITION BY: `toYYYYMM(timestamp)` | Bloom: `idx_id`, `idx_trace_id`

| Column | Type | Notes |
|--------|------|-------|
| id | String | Score ID |
| trace_id | String | FK to traces |
| name | String | Score name |
| value | Float64 | Numeric score |
| source | String | `API`, `ANNOTATION`, etc. |
| data_type | String | `NUMERIC`, `BOOLEAN`, `CATEGORICAL` |
| string_value | Nullable(String) | For non-numeric scores |
| timestamp | DateTime64(3) | |

---

## `langfuse` Database — Self-Hosted Langfuse

Self-hosted Langfuse writes directly to the `langfuse` database. This is the preferred source for tracing data — it preserves full application metadata including `message_id` for direct joins.

### `langfuse.traces` — LLM traces from self-hosted Langfuse

| Column | Type | Notes |
|--------|------|-------|
| id | String | Trace ID |
| name | String | Flow name (same values as cloud: `AskFast`, `V2_SIMPLE`, etc.) |
| session_id | String | **Join key to `chat_sessions.id`** |
| user_id | String | App user UUID |
| timestamp | DateTime64(3) | |
| metadata | Map(LowCardinality(String), String) | **Full app context** — see below |
| input | Nullable(String) | User's message text |
| output | Nullable(String) | AI response |
| project_id | String | Langfuse project ID |
| environment | LowCardinality(String) | `production`, `enterprise` |
| created_at | DateTime64(3) | |
| updated_at | DateTime64(3) | |
| event_ts | DateTime64(3) | |
| is_deleted | UInt8 | |

**Metadata contains** (Map keys): `message_id`, `user_id`, `user_email`, `user_twitter_handle`, `session_type`, `run_id`, `user_subscription_type`, `reasoning_effort`, `io_type`, `is_deep_research`, `integration_test`, `tags`.

### `langfuse.observations` — LLM observations from self-hosted Langfuse

| Column | Type | Notes |
|--------|------|-------|
| id | String | Observation ID |
| trace_id | String | FK to `langfuse.traces.id` |
| type | LowCardinality(String) | `GENERATION`, `SPAN` |
| name | String | Operation name |
| start_time | DateTime64(3) | |
| end_time | Nullable(DateTime64(3)) | |
| metadata | Map(LowCardinality(String), String) | Typed map |
| provided_model_name | Nullable(String) | LLM model used |
| usage_details | Map(LowCardinality(String), UInt64) | Token counts (`input`, `output`, `total`) |
| cost_details | Map(LowCardinality(String), Decimal(18,12)) | Cost breakdown |
| total_cost | Nullable(Decimal(18,12)) | |
| input | Nullable(String) | |
| output | Nullable(String) | |

---

## Joining Chat Messages to Langfuse Traces

> **CRITICAL — Linking `chat_messages` to traces:**
>
> There is **no shared ID** between `chat_messages.id` and trace `id`. The trace ID is a hex hash, the message ID is a UUID.
>
> **Self-hosted (`langfuse.traces`)** — use `metadata['message_id']` for a direct 1:1 join:
> ```sql
> SELECT m.id, m.human_message, t.id as trace_id, t.name as flow
> FROM default.chat_messages m
> INNER JOIN langfuse.traces t ON m.id = t.metadata['message_id']
> WHERE m.created_at >= today() - 1
> ```
>
> **Cloud export (`default.langfuse_traces`)** — no `message_id` in metadata. Join via `session_id` + timestamp proximity:
> ```sql
> -- Session-level: match messages to traces by session_id
> -- (requires toString() cast since chat tables use UUID, traces use String)
> SELECT m.id, m.human_message, t.id as trace_id, t.name as flow
> FROM default.chat_messages m
> INNER JOIN default.langfuse_traces t
>     ON toString(m.session_id) = t.session_id
>     AND abs(dateDiff('millisecond', m.created_at, t.timestamp)) < 1000
> WHERE m.created_at >= today() - 1
>     AND t.name NOT IN ('XAIChatModel', 'ChatLiteLLMRouter', 'fallback_grok')
> ```
>
> **Flow-level trace names** (1:1 with messages): `AskFast`, `V2_SIMPLE`, `V2_INSTANT`, `V2`, `V2_THINKING`, `Offline Research`, `LangGraph`, `Research`
>
> **Sub-traces to exclude** when counting per-message: `XAIChatModel`, `ChatLiteLLMRouter`, `fallback_grok`, `project_desc_review_agent`

### `posthog_events` — Product analytics events (16.5M rows)
| Column | Type | Notes |
|--------|------|-------|
| uuid | String | Event ID |
| timestamp | DateTime64(3) | |
| event | LowCardinality(String) | Event name |
| distinct_id | String | User identifier |
| properties | String | JSON event properties |
| person_id | Nullable(String) | PostHog internal ID — NOT the same as `users.id` |
| person_properties | Nullable(String) | JSON person properties |

> **CRITICAL — PostHog Identity Resolution:**
> - `person_id` is PostHog's internal identifier. It does **NOT** equal `users.id`. Never join `person_id` directly to the `users` table.
> - After PostHog identifies a user, batch exports merge all their `distinct_id` values under one `person_id`. This means naive `COUNT DISTINCT distinct_id` on visitors/registered/paid funnel steps can collapse to the **same number**.
> - To get the app user ID for joins to `users`/`invoices`/etc., use: `argMax(distinct_id, timestamp) AS identified_id` grouped by `coalesce(person_id, distinct_id)`. The latest `distinct_id` is typically the post-identification app user ID.
> - For funnel queries, use a **flag-based per-person approach**: group by person, set `maxIf` flags for each funnel step, then aggregate. See the working `ph_acquisition_funnel` query in `diver/app/workflow/assets/analytics/queries.py` as the reference pattern.
>
> ```sql
> -- Correct funnel pattern (flag-based, avoids distinct_id merge issue)
> WITH person_flags AS (
>     SELECT
>         coalesce(person_id, distinct_id) AS pid,
>         max(CASE WHEN event = '$pageview' THEN 1 ELSE 0 END) AS did_visit,
>         max(CASE WHEN event = 'login_started' THEN 1 ELSE 0 END) AS did_login,
>         max(CASE WHEN event = 'registration_complete' THEN 1 ELSE 0 END) AS did_register
>     FROM default.posthog_events
>     WHERE timestamp >= now() - INTERVAL 90 DAY
>     GROUP BY pid
> )
> SELECT
>     countIf(did_visit = 1) AS visitors,
>     countIf(did_login = 1) AS started_login,
>     countIf(did_register = 1) AS registered
> FROM person_flags
> ```

### `projects` — Crypto projects (23K rows)
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | |
| name | String | Project name |
| slug | Nullable(String) | URL slug |
| tier | Int32 | Project tier |
| description | Nullable(String) | |
| cryptorank_id | Nullable(Int32) | CryptoRank mapping |
| image | Nullable(String) | Logo URL |

### `user_subscriptions` — Subscription billing (26K rows)

> **IMPORTANT — Paying vs free**: To identify real paying users, filter out free trials:
> - `payment_source` values: `STRIPE`, `GOOGLEPAY`, `APPLEPAY` (real payment) vs `FREE` (not paying)
> - `subscription_type` values: `PRO`, `PLUS`, `MAX` (real plans) vs `PRO_TRIAL`, `MAX_TRIAL` (free trials)
> - `status` values are **UPPERCASE**: `ACTIVE`, `INACTIVE`
> ```sql
> -- Real paying users (ever paid)
> SELECT user_id FROM default.user_subscriptions
> WHERE payment_source != 'FREE'
>   AND subscription_type NOT IN ('PRO_TRIAL', 'MAX_TRIAL')
> -- Currently paying users
> SELECT user_id FROM default.user_subscriptions
> WHERE status = 'ACTIVE' AND payment_source != 'FREE'
> ```

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | |
| user_id | UUID | FK to users |
| subscription_type | Nullable(String) | `PRO`, `PLUS`, `MAX` (paid), `PRO_TRIAL`, `MAX_TRIAL` (free trials) |
| status | LowCardinality(Nullable(String)) | `ACTIVE` / `INACTIVE` (uppercase) |
| period | Nullable(String) | monthly/yearly |
| payment_source | Nullable(String) | `STRIPE` / `GOOGLEPAY` / `APPLEPAY` / `FREE` |
| start_date | Nullable(DateTime64(3)) | |
| end_date | Nullable(DateTime64(3)) | |
| rank | Int64 | |

### `bot_labels` — User classification labels (92K rows)
| Column | Type |
|--------|------|
| user_id | UUID |
| label | LowCardinality(String) |

### `invitation_codes` — Referral codes (530K rows)

> **This is the primary table for referral tracking.** Each row is a single-use invite code. To find all users referred by someone, query by `owner_user_id` and look at `invited_user_id`.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| code | String | The invite code string |
| is_used | Bool | Whether the code was redeemed (default false) |
| owner_user_id | Nullable(UUID) | FK to users — who generated/owns this code |
| owner_device_id | Nullable(String) | Device that generated the code |
| invited_user_id | Nullable(UUID) | FK to users — who signed up using this code |
| reused_count | Int64 | Number of times code was reused (default 0) |
| type | String | Code type |
| shared | Bool | Whether the code was shared (default false) |
| created_at | DateTime64(3) | |
| updated_at | DateTime64(3) | |
| _version | UInt64 | |

> **Referral analysis pattern:**
> ```sql
> -- Count referrals per user and how many converted to paying
> SELECT
>     owner_user_id,
>     countIf(invited_user_id IS NOT NULL) as successful_referrals,
>     countIf(invited_user_id IN (
>         SELECT user_id FROM default.user_subscriptions
>         WHERE status = 'ACTIVE' AND payment_source != 'FREE'
>     )) as currently_paying,
>     countIf(invited_user_id IN (
>         SELECT user_id FROM default.user_subscriptions
>         WHERE payment_source != 'FREE' AND subscription_type != 'PRO_TRIAL'
>     )) as ever_paid
> FROM default.invitation_codes
> WHERE owner_user_id = 'uuid-here'
> GROUP BY owner_user_id
> ```

### `feedbacks` — User feedback (970 rows)

### `message_interactions` — Message interactions (15K rows)

### `recommend_questions` — Recommended questions (2K rows)

### `invoices` — Payment invoices (7K rows)

### `mv_daily_user_stats` — Materialized view: daily user stats (823K rows)
Pre-aggregated daily user statistics. Use this for DAU/retention queries instead of scanning chat_messages.
