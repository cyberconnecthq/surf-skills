# Surf-Analytics ClickHouse — Product Data

Instance: `surf-analytics` (host resolved from AWS Secrets Manager at runtime)

Single `default` database containing product analytics tables synced from the application.

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

### `langfuse_traces` — LLM traces (7.6M rows, 335 GiB)
| Column | Type | Notes |
|--------|------|-------|
| id | String | Trace ID |
| name | Nullable(String) | Trace name |
| session_id | Nullable(String) | |
| user_id | String | |
| timestamp | DateTime64(3) | |
| environment | Nullable(String) | |
| project_id | Nullable(String) | |
| metadata | Nullable(String) | JSON metadata |
| tags | Array(String) | |
| input | Nullable(String) | JSON input |
| output | Nullable(String) | JSON output |

### `langfuse_observations` — LLM observations (129M rows, 1.29 TiB)
Detailed LLM call observations. Largest table.

### `langfuse_scores` — LLM evaluation scores (633K rows)

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
