---
name: surf-op-bad-case-audit
description: >
  Audit AI bad cases from user feedback. Pulls feedback from ClickHouse, traces from Langfuse,
  verifies factual claims against real data, classifies root causes, and updates the Notion bad case doc.
  Use when user asks to review bad cases, audit feedback, check AI accuracy, or says /surf-op-bad-case-audit.
---

# Bad Case Audit Skill

Systematic workflow for auditing AI bad cases from user feedback. Turns raw complaints into verified, root-cause-classified findings with Langfuse trace evidence.

**Depends on:** `surf-data-clickhouse` (for ClickHouse queries), `surf-data-langfuse-trace` (for trace analysis)

## When to Use

- Weekly bad case review (pairs with the diver auto-eval pipeline)
- After a spike in negative feedback
- Before/after deploying fixes to verify improvement
- When someone asks "what are users complaining about?"
- **30-day systematic audit** using the diver pipeline (see Scale Audit below)

## Overview

```
ClickHouse feedbacks (last 7 days)
  + chat_messages (user queries + AI responses)
  + langfuse_traces (tool calls, routing decisions)
  ──→ Verified bad cases with root cause classification
  ──→ Updated Notion bad case doc
```

### Daily Automated Pipeline

The diver eval pipeline runs **daily on Dagster** and evaluates 500 responses + 500 sentiments per day via Grok-4 (~$450/month). Located at `/Users/james/Desktop/James/Claude_code/diver/`.

**Daily schedule (UTC):**
| Time | Job | What it does |
|------|-----|-------------|
| 2 AM | langfuse_ingest | Sync Langfuse S3 → ClickHouse |
| 3 AM | bot_classification | Classify bot vs human users |
| 4 AM | sentiment_analysis | Keyword + thumbs_down → Grok-4 → message_sentiments |
| 5 AM | response_eval | Two-phase observation fetch → Grok-4 → response_eval_scores |
| 7 AM | eval_digest | Aggregate → eval_daily_digest → Slack alert if regression |
| 8 AM | analytics_refresh | Pre-compute dashboard JSON |

**Dashboard:** `/analytics/evals` — daily faithfulness trends, failure breakdown, worst observations with trace links.

**Alerting:** Slack webhook + auto GitHub issue creation when faithfulness drops > 0.05, hallucination spikes > 0.05, or confirmed failures > 2x.

### Manual Scale Audit

For one-time deep audits beyond the daily pipeline:

```
Phase 1: uv run python scripts/mine_faithfulness.py --days 30
  → Mines langfuse_scores (faithfulness_score records)
  → Outputs: data/faithfulness_mining/ (daily trends, tiers, enriched failures)

Phase 2: uv run python scripts/test_eval_pipeline.py --days 30 --sample 500 --concurrency 10
  → Runs sentiment + faithfulness + root cause eval via Grok-4
  → Uses improved judges with CJK support, severity scoring, fine-grained root causes
  → Outputs: message_sentiments, response_eval_scores (ClickHouse)
  → Repeat until candidates exhausted (anti-join skips already-evaluated)

Phase 3: uv run python scripts/cross_reference_failures.py --days 30
  → Joins sentiment + eval, uses evaluator's root cause codes directly
  → Outputs: data/cross_reference/ (confirmed + eval-only failures)

Phase 4: uv run python scripts/build_eval_set.py
  → Curates 50-100 representative cases as eval set
  → Outputs: data/eval_set/bad_cases.csv

Regression: uv run python scripts/run_regression.py
  → Re-evaluates eval set, reports improvements/regressions
```

### Root Cause Taxonomy

The response evaluator outputs these codes directly (no post-hoc disambiguation needed):

| Code | Description |
|------|-------------|
| `LLM_HALLUCINATION` | Claims fabricated from training memory, no tool source |
| `LLM_REASONING_ERROR` | Data available but model drew wrong conclusions |
| `LLM_CODE_ERROR` | Generated code has logic bugs |
| `LLM_INTERPRETATION_ERROR` | Model misread tool output |
| `TOOL_PARAM_ERROR` | Right tool, wrong parameters (wrong chain/token) |
| `TOOL_DATA_ERROR` | Tool returned stale, truncated, or malformed data |
| `TOOL_COVERAGE_GAP` | No tool exists for this query type |
| `ROUTER_MISROUTE` | Query sent to wrong agent/flow |
| `LANGUAGE_DETECT_ERROR` | Response language doesn't match user language |

### Sentiment Categories

The sentiment classifier now handles CJK languages natively and includes:
- `inaccuracy_complaint`, `doubt_uncertainty`, `frustration`, `correction`
- `feature_request`, `misunderstanding`, `positive_correction`
- `negative_general`, `false_positive`
- Each with a `severity` field: `low` | `medium` | `high` | `critical`

---

## Step 1: Pull Recent Feedback

Query the `default.feedbacks` table for the target period. Default is last 7 days.

```bash
scripts/pull-feedback --days 7
```

Or manually via the `surf-data-clickhouse` skill:

```sql
SELECT
    f.id,
    f.user_id,
    f.session_id,
    f.content,
    f.type,
    f.created_at
FROM default.feedbacks f
WHERE f.created_at >= now() - INTERVAL 7 DAY
ORDER BY f.created_at DESC
```

**Output:** `/tmp/bad-case-audit/feedback-raw.tsv`

### Cross-reference with chat messages

For each feedback, pull the associated chat session to see the user's query and AI response:

```sql
SELECT
    cm.session_id,
    cm.human_message,
    cm.ai_massage,  -- note: typo in column name is intentional
    cm.user_goal,
    cm.core_subject,
    cm.ai_action,
    cm.surf_platform,
    cm.lang,
    cm.created_at
FROM default.chat_messages cm
WHERE cm.session_id = '{session_id}'
ORDER BY cm.created_at
```

### Cross-reference with Langfuse traces

Match sessions to Langfuse traces for tool-level analysis:

```sql
SELECT
    lt.id as trace_id,
    lt.name,
    lt.session_id,
    lt.timestamp,
    lt.tags
FROM default.langfuse_traces lt
WHERE lt.session_id = '{session_id}'
ORDER BY lt.timestamp
```

**Langfuse session URL pattern:**
```
https://us.cloud.langfuse.com/project/cm6vcb1bb0akyad074n1zh0nr/sessions/{session_id}
```

---

## Step 2: Source-Trace Every Claim

**Core principle: Every number in an AI response must trace back to a tool call.** If a number has no tool-call source in the Langfuse observations, it came from LLM training memory — that's hallucination by definition.

### How to source-trace

For each factual claim in the AI response:

1. **Find the Langfuse observations** for the trace:
   ```sql
   SELECT id, name, type, start_time,
          substring(input, 1, 200) as input_preview,
          substring(output, 1, 200) as output_preview
   FROM default.langfuse_observations
   WHERE trace_id = '{trace_id}'
   ORDER BY start_time
   ```

2. **Map each number to its source.** For every price, supply, market cap, ATH, ratio, drawdown, or date in the AI response, find the tool call that produced it:
   - `token_trading_data` → current price, market cap, volume
   - `news_search` / `twitter_search` → event dates, qualitative claims
   - `execute_code` → calculated values (check the code for bugs)
   - `protocol_data` → TVL, yield data
   - No tool call found → **hallucinated from LLM training memory**

3. **Classify based on source:**

| Source | What to check | Root cause if wrong |
|--------|--------------|-------------------|
| No tool call | Number came from LLM memory | `LLM_HALLUCINATION` |
| Tool called on **wrong chain/wrong params** | LLM sent query to wrong target | `TOOL_PARAM_ERROR` |
| Tool returned data | Did tool return correct data? | `TOOL_DATA_ERROR` if wrong |
| Tool returned correct data | Did LLM use it correctly? | `LLM_INTERPRETATION_ERROR` if misread |
| `execute_code` ran code | Is the generated code correct? | `LLM_CODE_ERROR` if buggy |
| Correct data, correct code | Are labels/conclusions logical? | `LLM_REASONING_ERROR` if inverted |

### Decision Tree

```
For each factual claim in the AI response:
│
├── Can you find a tool call that produced this data?
│   ├── NO → LLM generated it from training memory
│   │         Root cause: LLM_HALLUCINATION
│   │
│   ├── YES, from a data tool (token_trading_data, news_search, etc.)
│   │   ├── Did the LLM call the tool with correct parameters?
│   │   │   └── NO  → Wrong chain, wrong token (symbol disambiguation), wrong date range
│   │   │             Root cause: TOOL_PARAM_ERROR
│   │   │             Check: does coin_id in response match the user's intended token?
│   │   ├── Did the tool return correct data?
│   │   │   ├── NO  → Root cause: TOOL_DATA_ERROR
│   │   │   └── YES → Did the LLM use it correctly?
│   │   │       ├── NO  → Root cause: LLM_INTERPRETATION_ERROR
│   │   │       └── YES → Check logical consistency (Step 2b)
│   │   │
│   │   └── Was the data truncated/partial?
│   │       └── YES → Root cause: TOOL_DATA_ERROR
│   │
│   └── YES, from execute_code (LLM-generated code)
│       ├── Were the inputs to the code correct?
│       │   └── NO  → Upstream LLM passed wrong parameters
│       │             Root cause: LLM_HALLUCINATION (for the inputs)
│       ├── Is the code logic correct?
│       │   └── NO  → LLM wrote buggy code (inverted comparisons, wrong formulas)
│       │             Root cause: LLM_CODE_ERROR
│       └── Code + inputs both correct → Check logical consistency (Step 2b)
│
Response contains tables, rankings, or comparisons?
├── YES → Check logical consistency (Step 2b below)
│   ├── Numbers correct but labels/ratings inverted?
│   │   Root cause: LLM_REASONING_ERROR
│   ├── Same metric contradicts itself across messages?
│   │   Root cause: LLM_REASONING_ERROR
│   └── Conclusion doesn't follow from the data shown?
│       Root cause: LLM_REASONING_ERROR
│
Complaint about incomplete answer?
├── YES → Check auto_router decision
│   ├── Routed to reporter_agent (V2_INSTANT)?
│   │   └── Should have gone to planner (V2_THINKING)
│   │       Root cause: ROUTER_MISROUTE
│   └── Routed to planner but still incomplete?
│       Root cause: TOOL_COVERAGE_GAP
│
Complaint about wrong language?
├── YES → Check language_detect output
│         Root cause: LANGUAGE_DETECT_ERROR
│
Other (UX, feature request, non-AI bug)?
└── Root cause: NON_AI_ISSUE
```

### Root Cause Codes

| Code | Component | Description |
|------|-----------|-------------|
| `LLM_HALLUCINATION` | reporter/planner LLM | LLM generated facts from training memory without tool support |
| `LLM_INTERPRETATION_ERROR` | reporter/planner LLM | Tool returned correct data but LLM misused it |
| `LLM_REASONING_ERROR` | reporter/planner LLM | Numbers are correct but reasoning/labels/comparisons are logically wrong |
| `LLM_CODE_ERROR` | calculate_agent + execute_code | LLM generated code with bugs (inverted logic, wrong comparisons) |
| `TOOL_PARAM_ERROR` | retriever_toolcall / agent LLM | LLM called the right tool but with wrong parameters (wrong chain, wrong token via ambiguous symbol, wrong filters) |
| `TOOL_DATA_ERROR` | tool implementation | Tool returned wrong, stale, or truncated data |
| `TOOL_COVERAGE_GAP` | retriever_toolcall | No tool exists for the data needed |
| `ROUTER_MISROUTE` | auto_router | Query routed to shallow flow instead of deep planning |
| `LANGUAGE_DETECT_ERROR` | language_detect | Wrong language classification |
| `NON_AI_ISSUE` | n/a | Auth, billing, UX, feature requests |

---

## Step 2b: Check Logical Consistency

**This step catches errors that pure data verification misses.** The AI can produce correct numbers but wrong reasoning — inverted risk labels, self-contradicting metrics, or conclusions that don't follow from the data. These are often more dangerous than wrong numbers because they look authoritative.

### Checklist for every response with tables or comparisons

**1. Inverted labels/ratings:** Do the status labels match the numbers?
- If a table ranks items by risk/safety/performance, verify the ordering is correct
- Check that "higher = better" or "lower = better" is applied consistently
- **Red flag:** A lower-risk option labeled as more dangerous than a higher-risk one

**2. Cross-message consistency:** Does the same metric stay stable across the conversation?
- Track key numbers (supply, market cap, price) across all messages
- **Red flag:** The same token's circulating supply changes by >10% between messages

**3. Math → conclusion alignment:** Does the conclusion follow from the data?
- If a table shows X is safer than Y, the conclusion should recommend X over Y
- If numbers show a 35% drop, the text shouldn't say "28% drop"
- **Red flag:** Data shows one thing, narrative says another

**4. Directional logic:** Are "more" and "less" applied correctly?
- Lower leverage → lower liquidation price → MORE room to fall → SAFER
- Higher volatility → MORE risk, not less
- Higher drawdown → WORSE performance, not better
- **Red flag:** Inverse relationships described as direct (or vice versa)

### Example: Leverage liquidation table (Session c91376f1)

The AI calculated correct liquidation prices but **inverted the risk labels**:

```
Entry: $90,000 BTC. Crash low: $62,822.

| Leverage | Liq Price | AI Said        | Correct Status      |
|----------|-----------|----------------|---------------------|
| 5x       | $72,000   | 🟡 Close call  | 🔴 LIQUIDATED       |
| 3x       | $60,000   | 🟢 Survived    | 🟢 Barely survived  |
| 2x       | $45,000   | 🔴 Wiped out   | 🟢 Survived easily  |
```

5x: price went below $72k → liquidated. 2x: price never near $45k → safe.
The AI swapped the status for 2x and 5x, telling users low leverage is MORE
dangerous — the exact opposite of reality.

### Example: Self-contradicting supply data (same session)

```
Message 5: "流通量 3.83亿 (383M), 总供应 5.045亿 (504.5M)"
Message 7: "流通供应 2.38亿 (238M), 最大供应 10亿 (1B)"
```

61% discrepancy in circulating supply within the same conversation. This
directly impacts the $50B market cap calculation the user asked about.

---

## Step 3: Verify Factual Claims

This is the critical step. For any complaint about wrong data, **verify the AI's claims against real data sources.**

### Price Verification

Use `external.coingecko_hour` in the `surf` ClickHouse instance:

```sql
-- Verify a specific price at a specific time
SELECT
    hour,
    symbol,
    price
FROM external.coingecko_hour
WHERE symbol = 'SOL'
  AND hour >= toDateTime('2026-02-12 00:00:00')
  AND hour <= toDateTime('2026-02-12 23:59:59')
ORDER BY hour DESC
LIMIT 5
```

```bash
scripts/verify-price --symbol SOL --date 2026-02-12
```

### ATH Verification

```sql
-- Find actual all-time high for a token in a year
SELECT
    toYear(hour) as year,
    max(price) as ath,
    argMax(hour, price) as ath_date
FROM external.coingecko_hour
WHERE symbol = 'ETH'
GROUP BY year
ORDER BY year DESC
```

### Historical Ratio Verification

```sql
-- Calculate token ratio over time (e.g., SOL/BTC)
SELECT
    toYear(s.hour) as year,
    avg(s.price / b.price) as avg_ratio,
    max(s.price / b.price) as peak_ratio,
    argMax(s.hour, s.price / b.price) as peak_date
FROM external.coingecko_hour s
JOIN external.coingecko_hour b
    ON s.hour = b.hour AND b.symbol = 'BTC'
WHERE s.symbol = 'SOL'
GROUP BY year
ORDER BY year
```

### Supply/TVL Verification

For circulating supply, market cap, TVL — cross-check against:
- CoinGecko API (via `token_trading_data` tool output in trace)
- DefiLlama (via `protocol_data` tool output in trace)
- On-chain data in ClickHouse `surf` instance

**Key principle:** Always note the **source** and **timestamp** of verification data. Include both the AI's claim and the verified value in the audit output.

For the full list of verification queries, see [references/verification-queries.md](references/verification-queries.md).

### Data Faithfulness Verification

Beyond price checks, verify **all factual claims** in the AI response — especially events, dates, project details, and causal narratives. The most dangerous hallucinations mix real facts with shifted context.

#### What to verify

| Claim Type | How to Verify | Common Hallucination Pattern |
|---|---|---|
| **Token sale / IDO** | CryptoRank, ICO Drops, project blog | Real sale details with wrong date (±1 year shift) or wrong recency ("most recent" vs "first") |
| **Partnership / integration** | Project Twitter, press releases | Real partnership from different time period attributed to wrong date |
| **Price at event** | `external.coingecko_hour` | Real price but from wrong date |
| **ATH / ATL** | `external.coingecko_hour` aggregation | ATH from different year cited as current year |
| **TVL / market cap** | DefiLlama, CoinGecko | Stale figure from LLM training cutoff |
| **Exchange listing** | Exchange announcement page | Real listing from wrong date or wrong exchange |
| **Fundraising round** | Crunchbase, The Block, CryptoRank | Real raise amount attributed to wrong project or round |
| **Tokenomics (supply, vesting)** | Project docs, on-chain data | Outdated schedule from training data |
| **Protocol mechanics** | Whitepaper, project docs | Correct for v1 but user is asking about v2 |

#### The "mixed-truth" hallucination pattern

This is the hardest pattern to catch. The AI produces a response where:
1. The **entity** is real (e.g., Buidlpad exists, Solayer exists)
2. The **numbers** are real (e.g., $10.5M raise, $0.35/token)
3. The **relationship** is real (e.g., Solayer DID sell on Buidlpad)
4. But the **temporal context** is wrong (e.g., January 2025, not January 2026)
5. Or the **recency** is wrong (e.g., "most recent" when it was actually "first")

**Example — Session `04346294`:**
```
AI claimed: "Buidlpad's most recent sale was Solayer (~Jan 17, 2026, $10.5M, $0.35/token)"
Reality:    Solayer was Buidlpad's FIRST sale (Jan 2025, not 2026)
            At least 3 later sales occurred (Sahara AI, Lombard, Falcon Finance)
            Financials ($10.5M, $0.35/token) are correct
Root cause: LLM_HALLUCINATION — training memory with +1 year date shift
```

#### Verification workflow for event claims

```
1. Web search: "[project] [event type] [date range]"
   - Use CryptoRank, The Block, CoinDesk as authoritative sources
   - Check the project's official blog / Twitter

2. Cross-reference dates:
   - AI says "January 2026" → search "January 2025" too (±1 year shift is common)
   - AI says "most recent" → verify chronological order of all events

3. Verify recency claims:
   - Search "[platform] all sales" or "[platform] history"
   - Build a timeline: was this really the latest event, or an earlier one?

4. Document the delta:
   - What did the AI claim? (exact quote)
   - What is the verified truth? (with source URL)
   - What's the error type? (wrong date, wrong recency, wrong attribution, stale data)
```

#### When no Langfuse traces exist

Some sessions (especially recent ones) may not have Langfuse traces yet (ingestion runs daily at 2 AM UTC). For these:
1. Check `chat_messages` for the full conversation
2. Verify factual claims via web search and ClickHouse price data
3. Add to `bad_cases.csv` with empty `observation_id` and `trace_id`
4. Note "No Langfuse traces — manual web verification" in `tool_usage_detail`
5. Re-evaluate once traces are ingested

---

## Step 4: Generate Audit Report

Structure findings into the standard bad case report format.

### Report Structure

```markdown
## Summary
{total} complaints this period. {n} root causes identified.

## Root Cause 1: {name} ({count} complaints)
**Severity:** P0/P1/P2
**What happened:** [traced evidence]
**Verified data:** [comparison table]
**Fix:** [recommendations]
**Affected sessions:** [Langfuse links]

## Root Cause 2: ...

## Data Verification Audit Results
[Table of AI claims vs verified values]

## Priority Fix Recommendations
[Table with priority, fix, impact, effort]

## All Langfuse Sessions
[Categorized list with links]
```

### Notion Update

Find and update the existing bad case Notion doc. The auto-pipeline creates docs titled "Bad Case {date} (Auto)" under the [Bad Case Doc](https://www.notion.so/2a70c7ec751f80289301df5374152075) parent page.

Use the Notion MCP tools:
1. `notion-search` for "Bad Case {date}"
2. `notion-fetch` to get current content
3. `notion-update-page` to replace with audited findings

---

## Step 5: Summary Statistics

After the audit, generate summary stats:

```sql
-- Feedback volume trend (last 4 weeks)
SELECT
    toStartOfWeek(created_at) as week,
    count() as total_feedback,
    countIf(type = 'thumbs_down') as thumbs_down,
    countIf(type = 'feedback') as text_feedback
FROM default.feedbacks
WHERE created_at >= now() - INTERVAL 28 DAY
GROUP BY week
ORDER BY week DESC
```

---

## Odin-Flow Systemic Issues (Why 77% Hallucination)

The following architectural issues in odin-flow create a systemic hallucination pipeline. Understanding these helps identify root causes faster during audits.

### The Cascade

```
User Query → Router (97% V2/V2_PRO/V2_INSTANT, NOT V2_THINKING)
  → Planner QA gate is BYPASSED (planner only reachable for V2_THINKING = 3%)
  → Router selects common_agent or reporter_agent
  → Tools may return [Empty Result] — no warning flag
  → Reporter receives empty/insufficient data
  → Reporter prompt says: "proceed with analysis" and "do NOT request additional data"
  → Reporter fabricates from parametric knowledge
  → No validation checks fabricated claims against tool data
  → Thinking tags may leak to user
  → User sees authoritative-looking analysis built on nothing
```

### Key Code Locations

| Issue | File | Lines | Quick Check |
|---|---|---|---|
| Planner unreachable | `router_node.py` | 24-51, 356-361 | `get_valid_router_agents()` excludes planner |
| Empty data no warning | `dataframe_markdown.py` | 17-18 | `if df.empty: return ""` |
| Hallucination directive | `agent_team_v2.py` | 66-77 | Line 74: "Work with whatever data is available" |
| Reporter "proceed" | `v2_reporter.md` | 11 | "If data appears insufficient, proceed with analysis" |
| Token disambiguation | `token_price.py` | 219-227 | `mapping.items[0]` — takes first match blindly |
| Thinking leak | `simple_react_agent.py` | multiple | Adds `<thinking>` tags to content |
| Truncation buried | `model.py` | 204-238 | Truncation notice inside XML closure |

### During Audits, Check These

1. **Was the planner involved?** Check `auto_router` output in trace. If `session_type != V2_THINKING`, planner was bypassed.
2. **Were tool results empty?** Look for `[Empty Result]` in the reporter's input context.
3. **Did the retriever PASS?** If retriever output is `"PASS"`, zero tools were called — any specific claims are fabricated.
4. **Are thinking tags visible?** Search response for `<think>`, `<thinking>`, or internal tool names (`surf_faq`, `language_detect_01`).
5. **Was the right token resolved?** Check `coin_id` in `token_trading_data` output vs user's intended token.

### Fix Recommendations Summary

Full details: `data/eval_set/odin_flow_fix_recommendations.md`

| Priority | Fix | Expected Impact |
|---|---|---|
| P0 | Data sufficiency gate (prompt changes + empty data warning) | ~60% hallucination reduction |
| P0 | Enable planner for V2/V2_PRO or add data quality gate node | ~40% additional reduction for PRO |
| P0 | Strip thinking tags from output | Eliminates info leak |
| P1 | Token disambiguation with chain_id context | Reduces TOOL_PARAM_ERROR (8.6%) |
| P1 | Language detection for mixed input | Fixes CJK UX |
| P1 | Retriever PASS decision guard | Prevents no-data fabrication |

---

## Common Pitfalls

### "The price is wrong" usually means the context is wrong
In our Feb 18 audit, all 16 "wrong price" complaints had **correct live prices**. Users were actually complaining about:
- Hallucinated historical data (peak dates, ATH values, ratios)
- Wrong-year price references (using 2024 data for 2026 events)
- Inflated metrics (TVL, supply) generated from LLM memory
- Outdated data from LLM training cutoff

**Always verify the live price first**, then check the surrounding context the LLM generated.

### No source = hallucinated
The single most reliable audit rule: **every number must trace back to a tool call.** If you see a price, ATH, supply figure, TVL, drawdown percentage, or date in the AI response and cannot find the tool call that produced it in the Langfuse observations, it's hallucinated from LLM training memory. Don't debate whether the number "seems right" — if there's no source, flag it.

### Trace the full pipeline, not just the output
A "shallow answer" complaint is usually a routing issue (`auto_router` → `reporter_agent`), not a model quality issue. Check:
1. What did `language_detect` output?
2. What did `retriever_toolcall` decide to call?
3. What did `auto_router` decide? (reporter vs planner)
4. If reporter: was the data sufficient for a good answer?

### Code execution doesn't mean code is correct
When `calculate_agent` calls `execute_code`, the code runs successfully and returns results. But the LLM-generated code can have inverted comparisons (`>` instead of `<`), wrong input values, or flawed formulas. **Always read the actual code** in the Langfuse observation — don't trust code output just because it executed without errors.

### Correct numbers ≠ correct reasoning
The most dangerous errors are logically inverted conclusions built on correct math. A leverage table with right liquidation prices but swapped risk labels. A comparison where the "safer" option is labeled "riskier." A supply number that changes between messages. These pass numerical spot-checks but give users the opposite of correct guidance. **Always read tables as a human would** — do the labels make sense given the numbers?

### Check tool call parameters, not just tool outputs
The tool can be the right tool but called with wrong parameters. Two known sub-types:
- **Chain mismatch (8a):** A GPS token search on Ethereum mainnet returns 0 results — not because GPS doesn't exist, but because GPS is on Base chain. Always verify: did the LLM send the query to the correct chain?
- **Token disambiguation (8b):** `token_trading_data` for "FUN" returns FunFair (`coin_id: funfair`, price $0.001) instead of Football.Fun (price $0.034). The tool silently resolves ambiguous symbols to the wrong token. Always check: does the `coin_id` in the response match the token the user is actually asking about?

Both produce cascading failures: wrong data in → hallucinated calculations on top → self-contradiction when the user corrects.

### Don't trust the AI's claimed methodology
The AI may say "I performed a multi-chain scan including Base, BSC, Ethereum..." but the actual tool calls only queried Ethereum. Compare the AI's stated scope against the actual tool calls in Langfuse. If the AI claims to have checked something it didn't, that's hallucinated methodology.

### Watch for cascading compound failures
The most dangerous bugs aren't single-point failures — they're cascading chains where each mistake enables the next. Session 70742ee0 is the canonical example:
1. `TOOL_PARAM_ERROR` — `token_trading_data` resolved "FUN" to the wrong token (FunFair instead of Football.Fun)
2. `LLM_HALLUCINATION` — AI fabricated "+11.6% vs ICO" on top of the wrong data (no tool returned this number)
3. `LLM_REASONING_ERROR` — AI contradicted itself across messages (+11.6% in Message 2, -43% in Message 3)
4. `ROUTER_MISROUTE` — all 3 messages went V2 instead of V2_THINKING, reducing the depth of analysis

If any single step had been caught, the cascade stops. When auditing, don't stop at the first root cause — trace the full chain.

### Don't trust complaint categorization at face value
Users say "wrong price" but mean "wrong historical context." Users say "incomplete" but mean "you used the wrong tool." Always trace back to the actual component failure.

### Eval pipeline has false positives too
Our own eval (response_evaluator) can flag valid responses as hallucination. Known triggers:
- **Non-English responses:** Evaluator struggles to match Korean/Chinese claims against English tool output
- **2026 dates:** Evaluator may flag 2026 data as "future/fabricated" (2026 IS the current year)
- **Computed values:** When the model correctly calculates percentages from tool data, eval may not match the computed result back to the raw tool output
- **Rule:** If eval scores 0 faithfulness but the tool DID return relevant data, manually verify before classifying as hallucination. Check trace `e9760404` (PEPE Korean) as a canonical false positive example.

### Retriever PASS doesn't always mean "no data needed"
When `retriever_toolcall` returns `"PASS"`, it means the retriever LLM decided no tools were necessary. This is correct for greetings and simple definitions but wrong for technical or analytical queries. If the reporter's response contains specific numbers/data and the retriever said PASS, those numbers are fabricated from parametric knowledge. Check `auto_router` → if PASS + analytical query = likely hallucination pipeline.

---

## Agent Pipeline Reference

| Step | Node | Model | What to check |
|------|------|-------|---------------|
| Tool selection | `retriever_toolcall` | XAIChatModel (Grok) | Did it call the right tools? Did it PASS when it shouldn't have? |
| Language | `language_detect` | (embedded) | Correct language code? Returns `"none"` for mixed-language? |
| Routing | `auto_router` | deepseek-v3p1 | reporter vs planner? V2_INSTANT for analytical query = misroute |
| Quick report | `reporter` (V2_INSTANT) | FireworksDeepSeekChatModel | `<think>` tags leaked? Sufficient for the query? |
| Deep plan | `team_planner` (V2_THINKING) | gemini-3-flash-preview | Multi-step plan correct? Did it pass correct inputs? |
| Research | `common_agent` / `search_agent` | grok-4-1-fast-reasoning | Tool calls + synthesis. **Check tool call params (chain, address, filters)** |
| On-chain | `evm_onchain_agent` | grok-4-1-fast-reasoning | ERC-20 balances, tx receipts, contract calls. Has the right tools but may not be routed to |
| Calculation | `calculate_agent` | grok-4-1-fast-reasoning | **Read the generated code.** Check for inverted comparisons, wrong inputs |
| Code execution | `execute_code` | (sandbox) | Code ran successfully ≠ code is correct. Verify logic. |
| Image analysis | `multimodal` | ChatGoogleGenerativeAI (Gemini) | May assume year is 2024 (training cutoff). Check date interpretation. |
| Follow-up | `followup` | kimi-k2-instruct-0905 | Suggested questions. May default to English if language_detect returned "none" |

### Session Type → Flow Mapping

| Session Type | % Traffic | Entry Point | Planner? | Notes |
|---|---|---|---|---|
| `V2_INSTANT` | ~50% | reporter_agent directly | NO | No tools, no QA — most hallucination-prone |
| `V2` | ~30% | LLM-based router | NO | Router picks common_agent or reporter |
| `V2_PRO` | ~15% | LLM-based router | NO | Same as V2 but premium users |
| `V2_THINKING` | ~3% | planner | YES | Full QA pipeline — lowest hallucination rate |

When auditing, always check `session_type` first. If it's NOT `V2_THINKING`, the planner was bypassed.

## Reference Files

| Need | Reference |
|------|-----------|
| Known root cause patterns and how to fix them | [root-cause-patterns.md](references/root-cause-patterns.md) |
| ClickHouse queries for fact-checking AI claims | [verification-queries.md](references/verification-queries.md) |
| Past audit findings (learnings from previous audits) | [audit-history.md](references/audit-history.md) |
