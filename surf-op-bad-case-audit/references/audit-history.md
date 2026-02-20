# Audit History

Findings from past bad case audits. Serves as institutional memory — prevents re-investigating known issues and tracks whether fixes actually worked.

---

## Audit: Feb 18, 2026 — 30-Day Systematic Eval

**Period:** Jan 20 – Feb 17, 2026
**Method:** Automated mining of 34K faithfulness_score records from langfuse_scores (odin-flow's real-time subagent_faithfulness_judge), cross-referenced with user DISLIKE interactions and feedback forms. No manual session review.
**Tools:** `scripts/mine_faithfulness.py`, `scripts/cross_reference_failures.py`, `scripts/build_eval_set.py`
**Eval set:** `data/eval_set/bad_cases.csv` (100 curated cases)

### Key Metrics (30 days)

| Metric | Value |
|---|---|
| Total faithfulness scores | 33,988 |
| Overall average | 0.457 |
| Severe failures (< 0.3) | 14,324 (42.1%) |
| Complete hallucinations (score = 0) | 11,977 (83.6% of severe) |
| Unique sessions with severe failures | 12,922 |
| User DISLIKE interactions | 68 (across 61 sessions) |
| Feedback form submissions | 246 |

### Daily Trend

Average faithfulness was relatively stable at ~0.49 from Jan 25 – Feb 13, then dropped sharply:

| Period | Avg Faith | P25 | P50 | Notes |
|---|---|---|---|---|
| Jan 25 – Feb 13 (stable) | 0.490 | 0.000 | 0.59 | Normal operating range |
| Feb 15 | 0.337 | 0.000 | 0.000 | Regression start |
| Feb 16 | 0.311 | 0.000 | 0.000 | Regression deepens |
| Feb 17 | 0.306 | 0.000 | 0.000 | Worst day |

**Feb 15-17 regression:** Median dropped from 0.59 to 0.00, indicating a systematic change (likely model or prompt update) that caused majority of responses to score 0.

### Phase 2: Diver Eval Results (Tier 1 — 68 DISLIKE Sessions)

**Method:** Ran diver eval pipeline (`scripts/test_eval_pipeline.py`) with Grok-4 on all 68 DISLIKE sessions. Evaluated integrity, faithfulness, and root cause for each observation. Sentiment analysis classified user messages to distinguish genuine complaints from false positives.

**Execution:** 3 parallel processes x 10 concurrent Grok-4 calls. Two-phase ClickHouse query strategy (lightweight metadata → truncated data fetch). Total: ~470 Grok-4 calls.

| Metric | Value |
|---|---|
| Sessions evaluated | 68 |
| Observations evaluated | 438 |
| Pass | 8 (1.8%) |
| Fail | 430 (98.2%) |
| Avg faithfulness | 0.563 |
| Integrity pass rate | 10.5% |
| Hallucination rate | 58.4% |

### Failure Category Distribution (from diver eval)

| Failure Category | Count | % |
|---|---|---|
| `reasoning_failure` | 346 | 80.5% |
| `retrieval_failure` | 39 | 9.1% |
| `tool_failure` | 32 | 7.4% |
| `coverage_gap` | 11 | 2.6% |
| `data_freshness` | 2 | 0.5% |

### Root Cause Distribution (after cross-reference mapping)

| Root Cause | Count | % | Notes |
|---|---|---|---|
| `LLM_HALLUCINATION` | 343 | 79.8% | Still dominant but less extreme than Phase 1 mining (97%) |
| `TOOL_PARAM_ERROR` | 37 | 8.6% | Wrong chain, wrong token disambiguation |
| `TOOL_DATA_ERROR` | 34 | 7.9% | Stale data, truncated OHLC, API errors |
| `TOOL_COVERAGE_GAP` | 13 | 3.0% | No tool available for user's question |
| `LLM_REASONING_ERROR` | 3 | 0.7% | Correct data, wrong conclusions |

### Sentiment Analysis (DISLIKE Sessions)

Of 61 messages with DISLIKE interactions, sentiment classification found:

| Sentiment | Count | % |
|---|---|---|
| `false_positive` | 41 | 67% |
| `doubt_uncertainty` | 7 | 11% |
| `correction` | 6 | 10% |
| `inaccuracy_complaint` | 3 | 5% |
| `frustration` | 3 | 5% |
| `negative_general` | 1 | 2% |

**Key finding:** 67% of DISLIKE interactions are false positives (user disagreement, feature requests, not quality complaints). Only 16 (26%) are genuine accuracy-related complaints.

### Confirmed vs Silent Failures

| Category | Count |
|---|---|
| Confirmed (user complained + eval failed) | 7 |
| Silent (eval-only, no user complaint) | 423 |
| **Total failures** | **430** |

**98.4% of failures are silent** — users don't report them. The 7 confirmed failures are dominated by `LLM_HALLUCINATION` (6/7).

### Eval Set (Phase 4)

Curated 100 representative bad cases in `data/eval_set/bad_cases.csv`:

| Root Cause | Count |
|---|---|
| `LLM_HALLUCINATION` | 66 |
| `TOOL_PARAM_ERROR` | 17 |
| `TOOL_COVERAGE_GAP` | 9 |
| `TOOL_DATA_ERROR` | 5 |
| `LLM_REASONING_ERROR` | 3 |

### Comparison: Phase 1 Mining vs Phase 2 Diver Eval vs Manual Audit

| Root Cause | Manual (33 complaints) | Phase 1 Mining (34K scores) | Phase 2 Diver Eval (438 obs) |
|---|---|---|---|
| `LLM_HALLUCINATION` | 33% | 97% | 79.8% |
| `ROUTER_MISROUTE` | 39% | N/A | N/A (not captured by eval) |
| `TOOL_PARAM_ERROR` | — | N/A | 8.6% |
| `TOOL_DATA_ERROR` | 15% | N/A | 7.9% |
| `TOOL_COVERAGE_GAP` | — | N/A | 3.0% |
| `LLM_REASONING_ERROR` | — | N/A | 0.7% |
| `LANGUAGE_DETECT_ERROR` | 9% | N/A | N/A (not captured by eval) |

The Phase 2 diver eval fills the gap between Phase 1 mining (only captures hallucination) and manual audit (only captures user complaints). It reveals tool-related failures (TOOL_PARAM_ERROR + TOOL_DATA_ERROR = 16.5%) that were invisible to the faithfulness judge.

### Actions Taken (Feb 19, 2026)

Based on these findings, the following improvements were deployed:

1. **Sentiment classifier rewritten** (`app/prompts/sentiment_classifier.md`) — Added CJK examples (ZH/KO/JA) for all categories, 3 new categories (`feature_request`, `misunderstanding`, `positive_correction`), severity field (`low`/`medium`/`high`/`critical`), tightened keyword pre-filter to reduce false positives
2. **Response evaluator rewritten** (`app/prompts/response_evaluator.md`) — Replaced 5 coarse failure codes with 10 fine-grained audit taxonomy codes (`LLM_HALLUCINATION`, `LLM_REASONING_ERROR`, `LLM_CODE_ERROR`, `LLM_INTERPRETATION_ERROR`, `TOOL_PARAM_ERROR`, `TOOL_DATA_ERROR`, `TOOL_COVERAGE_GAP`, `ROUTER_MISROUTE`, `LANGUAGE_DETECT_ERROR`). Added relevance scoring, completeness scoring, and tool usage evaluation.
3. **Dagster pipeline activated** — All eval schedules set to RUNNING (langfuse_ingest 2AM, sentiment 4AM, response_eval 5AM, eval_digest 7AM). Two-phase observation fetch for eval_faithfulness. Date scoping for both assets.
4. **ClickHouse schemas updated** — `message_sentiments` +severity column, `response_eval_scores` +relevance_score, +completeness_score, +tool_usage_pass, +tool_usage_detail
5. **Alerting added** — Slack webhook + auto GitHub issue creation on regression (faithfulness drop >0.05, hallucination spike >0.05, confirmed failures >2x)
6. **Dashboard added** — `/analytics/evals` with daily trends, failure breakdown, worst observations table
7. **30-day backfill started** — Running `test_eval_pipeline.py --days 30 --sample 500 --concurrency 10` with improved judges

### Remaining Next Steps

1. **Investigate Feb 15-17 regression** — What changed? Model update? Prompt change? Tool failure?
2. **Run Tier 2 eval** on stratified sample of 200 sessions with faith < 0.3 (no user signal)
3. **Add routing quality metric** to complement faithfulness scoring — captures ROUTER_MISROUTE
4. **Fix top root causes** — LLM_HALLUCINATION (add historical_price_data tool), TOOL_PARAM_ERROR (chain propagation, token disambiguation)
5. **Improve faithfulness judge coverage** to overlap with user-interacted sessions

---

## Audit: Feb 19, 2026 — Phase 2 Deep Dive + Odin-Flow Systemic Analysis

**Period:** Feb 18-19, 2026 (deep-dive on Phase 2 eval results)
**Method:** Trace-level deep-dive on 12 specific observations from response_eval_scores, followed by comprehensive odin-flow codebase analysis
**Tools:** `scripts/test_eval_pipeline.py` (30-day backfill), ClickHouse trace queries, odin-flow source code analysis
**Output:** `data/eval_set/odin_flow_fix_recommendations.md`, updated eval sets

### Backfill Results

| Table | Before | After | Delta |
|---|---|---|---|
| `message_sentiments` | 61 | 561 | +500 (30-day backfill via async concurrent Grok-4) |
| `response_eval_scores` | 0 | 818 | +818 (two-phase observation fetch + concurrent eval) |

### Pipeline Improvements Made

1. **Async concurrent API calls** — Rewrote sentiment step from sequential sync to async with `asyncio.Semaphore(concurrency)`. 5x speedup.
2. **Incremental writes every 50** — Added `_flush_sentiments()` to write to ClickHouse every 50 rows, preventing data loss on stalls/timeouts.
3. **60s timeout** on xAI client to prevent hanging on unresponsive API calls.
4. **Fixed Step 3 trace lookup** — Was querying `langfuse_traces` for trace IDs but LIMIT 1500 only covered most recent ~1 hour due to 37K traces/day. Fixed to query `DISTINCT trace_id FROM langfuse_observations WHERE parent_observation_id IS NULL` directly, avoiding data lag mismatch.

### Cross-Reference Results

| Method | Confirmed Failures |
|---|---|
| Direct message_id join | 8 |
| Session-based join via langfuse_traces | 40 |
| Eval-only (no user complaint) | 778 |

### Eval Set Built

| File | Cases | Purpose |
|---|---|---|
| `data/eval_set/bad_cases.csv` | 56 | Stratified across 10 root cause categories |
| `data/eval_set/confirmed_failures.csv` | 8 | User complained AND eval failed |

### Trace Deep-Dive: 5 LLM_HALLUCINATION Traces

Analyzed 5 traces with agent `ae47ed1`:

| Trace ID | Pattern | Key Finding |
|---|---|---|
| `47af240a` | Cascading from conversation history | Prior turns had fabricated Uniswap v4 metrics; reporter continued using them |
| `4591cc60` | Parametric knowledge extrapolation | Tool returned basic 0G metadata; reporter fabricated $325M funding, specific investors |
| `4324b27e` | Empty data → fabrication | Tools returned project lists but no technical depth on impermanent loss |
| `3dc2b9b4` | Retriever PASS → zero tools | Retriever said PASS for Solana oracle question; reporter fabricated entire analysis + thinking leak |
| `e9760404` | **Eval false positive** | PEPE query: tool returned valid OHLC data, model computed correct percentages — eval wrongly scored as hallucination |

**3 failure modes identified:**
1. **Gap-fill fabrication** (3/5): Tool data empty/tangential, model fills from parametric knowledge
2. **Over-extrapolation** (1/5): Tool returns some data, model massively extends
3. **Eval false positive** (1/5): Tool returned good data, model used it correctly

**4 out of 5 traces had `<think>` block leaks** to users.

### Trace Deep-Dive: Non-Hallucination Failures

Analyzed 7 traces with agent `adc48c6`:

| Root Cause | Trace ID | Finding |
|---|---|---|
| `LANGUAGE_DETECT_ERROR` | `02dd6625` | Russian + Korean mixed input → detector returned `"none"` → followup in English |
| `LLM_REASONING_ERROR` | `9bd8595d`, `bebb8aea`, `af99e442` | All 3: verifier ignored unsupported `"extra": {}` field in data, scored 1.0 instead of 0.0 |
| `ROUTER_MISROUTE` | `016ef86c` | Conceptual query → V2_INSTANT → DeepSeek thinking model → thinking tags leaked |
| `ROUTER_MISROUTE` | `23633b7f` | Wrapped BTC query → retriever called stablecoin industry tag → irrelevant data (self-recovered via planner) |
| `LLM_INTERPRETATION_ERROR` | `3afde82e` | Gemini assumed year 2024 for image analysis → reporter confused by conflicting timestamps |

### Odin-Flow Systemic Analysis (9 Issues)

Comprehensive analysis of odin-flow codebase (agent `a64492f`) identified these architectural root causes for the 77% hallucination rate:

| # | Issue | File | Impact |
|---|---|---|---|
| 1 | **Planner unreachable for 97% of traffic** | `router_node.py:24-51,356-361` | No QA gate for V2/V2_PRO/V2_INSTANT |
| 2 | **Empty results marked as `[Empty Result]` with no warning** | `model.py:154-171`, `dataframe_markdown.py:17-18` | Reporter fabricates from empty data |
| 3 | **Reporter instructed to "proceed with analysis" when data insufficient** | `agent_team_v2.py:74`, `v2_reporter.md:11` | Explicit hallucination directive |
| 4 | **Token disambiguation takes `items[0]` blindly** | `token_price.py:219-227` | Wrong chain/token resolved silently |
| 5 | **Thinking tags not stripped from output** | `simple_react_agent.py`, `content_parser.py` | Internal reasoning exposed to users |
| 6 | **Truncation notice buried in XML tags** | `model.py:204-238` | Reporter misses data completeness |
| 7 | **No validation between tool output and LLM response** | `router_node.py` (entire flow) | Fabricated claims pass through unchecked |
| 8 | **Default routing ignores empty available_data** | `router_node.py:57-64, 280-311` | Routes to reporter even with no data |
| 9 | **Retriever PASS decision has no fallback** | `retriever.py:95-113` | Zero-tool queries → zero data → fabrication |

### Fix Recommendations (9 Fixes, 3 Priority Tiers)

Full details in `data/eval_set/odin_flow_fix_recommendations.md`.

| Fix | Priority | Impact Estimate |
|---|---|---|
| Data sufficiency gate (prompt + empty data warning) | P0 | ~60% hallucination reduction |
| Enable planner for V2/V2_PRO or add data quality node | P0 | ~40% additional reduction for PRO |
| Strip thinking tags from output | P0 | Eliminates info leak |
| Token disambiguation with chain context | P1 | Reduces TOOL_PARAM_ERROR (8.6%) |
| Language detection for mixed input | P1 | Fixes CJK UX |
| Retriever PASS decision guard | P1 | Prevents no-data fabrication |
| Retriever tool selection guardrails | P2 | Reduces misroute |
| Multimodal model time context | P2 | Fixes interpretation errors |
| Eval false positive reduction | P2 | Improves eval accuracy |

### Cascade Estimate

If P0 fixes are implemented together:
- LLM_HALLUCINATION: 79.8% → ~25-30%
- Thinking leaks: 4/5 → 0
- Overall failure rate: 98.2% → ~40-50%

---

## Audit: Feb 20, 2026 — Session 04346294 (Buidlpad Sale Hallucination)

**Type:** User-reported session audit
**Session:** `04346294-6abc-4aca-97c8-93e1a74e68ca`
**Messages:** 2 (English, iOS)
**Topic:** Buildpad/Buidlpad recent token sales

### Pattern: Mixed-Truth Hallucination (Real Facts + Wrong Temporal Context)

This session demonstrates the most insidious hallucination pattern: the AI produces responses where the entity, numbers, and relationship are all real, but the temporal context is shifted by exactly one year.

### Messages

| # | User Query | Key AI Claims |
|---|---|---|
| 1 | "did buildpad recently do any sale" | "Buidlpad recently conducted token sales, with the most recent being Solayer's community sale that concluded around January 17, 2026" |
| 2 | "when and what was their most recent sale?" | "Buidlpad's most recent token sale was for Solayer, ~Jan 17, 2026. Raised $10.5M at $0.35/token" |

### Verification Results

| Claim | AI Said | Reality | Verdict |
|---|---|---|---|
| Platform exists | Buidlpad is real | Buidlpad is real (founded by ex-Binance exec Erick Zhang) | **CORRECT** |
| Solayer sold on Buidlpad | Yes | Yes — Solayer was Buidlpad's **inaugural** community sale | **CORRECT relationship, WRONG recency** |
| Sale price | $0.35/LAYER | $0.35/LAYER (30M tokens, 3% of supply) | **CORRECT** |
| Raise amount | $10.5M | $10.5M hard cap | **CORRECT** |
| Sale date | ~January 17, 2026 | **January 16, 2025** (postponed from Jan 13-14 due to 15x oversubscription) | **WRONG — off by exactly 1 year** |
| "Most recent" sale | Yes | **NO** — it was the FIRST sale. At least 3 later sales: Sahara AI, Lombard, Falcon Finance (Sept 2025) | **WRONG — first, not most recent** |

**Sources:** CryptoRank, The Block, ICO Drops, PANews, CoinLaunch, TheNewsCrypto, IBTimes

### Root Cause

`LLM_HALLUCINATION` — Classic training-memory hallucination. The model retrieved real Buidlpad/Solayer facts from parametric knowledge but:
1. Shifted the date forward by exactly 1 year (Jan 2025 → Jan 2026)
2. Incorrectly labeled Solayer as "most recent" when it was the first sale
3. No tool calls were made (no Langfuse traces exist for this session)

### Unique Characteristics

- **No Langfuse traces** — Session created Feb 19, 2026 22:29 UTC. No traces ingested yet (daily Langfuse ingest runs at 2 AM UTC).
- **No user feedback** — No thumbs down or feedback form for this session.
- **iOS platform** — V2_INSTANT likely (no deep planning).
- **This case is only catchable by data faithfulness verification** — the numbers all "look right" and would pass a naive fact-check that only verifies individual data points without checking temporal context.

### Key Takeaway

Mixed-truth hallucinations are the hardest to detect automatically. The AI gets 4 out of 6 facts correct, and the 2 errors (date shift, recency inversion) require external knowledge to catch. This pattern argues for:
1. A **temporal verification step** — when AI cites dates, verify they match the current year
2. A **recency verification step** — when AI says "most recent", verify chronological ordering
3. **Web search grounding** for event claims — don't rely on parametric knowledge for "when did X happen?"

---

## Audit: Feb 18, 2026

**Period:** Feb 11–18, 2026
**Total complaints:** 33
**Notion doc:** [Bad Case 2.18 (Auto)](https://www.notion.so/30b0c7ec751f81fd85c2e2c65fc5dcfd)

### Root Causes Found

| Root Cause | Count | % | Status |
|---|---|---|---|
| `ROUTER_MISROUTE` — auto_router sends analytical queries to reporter_agent | 13 | 39% | Open |
| `LLM_HALLUCINATION` — LLM generates historical data from training memory | 11 | 33% | Open |
| `TOOL_DATA_ERROR` — token_trading_data returns truncated OHLC data | 5 | 15% | Open |
| `LANGUAGE_DETECT_ERROR` — Mixed-language Korean misclassified as English | 3 | 9% | Open |
| `NON_AI_ISSUE` — Auth bugs, billing display, feature requests | 5 | — | N/A |

### Key Discovery

**Original diagnosis was wrong.** The auto-pipeline flagged 16 complaints as "wrong price from token_trading_data." After verification against ClickHouse `external.coingecko_hour`:
- SOL $81.70 on Feb 12 — **CORRECT**
- ONDO $0.292 on Feb 12 — **CORRECT**
- ETH $2,827 on Feb 18 — **CORRECT**

The real issue: users were complaining about **hallucinated historical context** around the correct live price (wrong peak dates, wrong ATH values, wrong-year references, inflated TVL).

### Verified Data Errors

| Claim | Actual | Error |
|---|---|---|
| ETH 2025 ATH: $2,827 (Feb) | $4,926 (Aug) | 74% off, wrong month |
| 余霜 SOL: $112.04 | ~$83 (Feb 2026) | Wrong year (used 2024 price) |
| ONDO TVL: $14B+ | ~$1.4B | ~10x inflated |
| LINK supply: 588.1M | ~708M | Outdated by 120M |
| SOL/BTC 2025 peak: Jan | Sep | Wrong by 8 months |
| SOL/BTC 2021 peak: Sep | Nov | Wrong by 2 months |

### Langfuse Sessions

| Session | Issue | Root Cause |
|---|---|---|
| 35bc6ab3 | SOL price correct, ratios/dates hallucinated | LLM_HALLUCINATION |
| df6aff4d | ETH ATH $2,827 vs actual $4,926 | LLM_HALLUCINATION |
| b665c5bb | ONDO price correct, TVL hallucinated | LLM_HALLUCINATION |
| b4361aa7 | Used 2024 SOL price for 2026 event | LLM_HALLUCINATION |
| c7fd8ce2 | ETH historical context hallucinated | LLM_HALLUCINATION |
| e6d5e46c | LINK supply outdated + shallow routing | LLM_HALLUCINATION + ROUTER_MISROUTE |
| e2597534 | bankr NFT shallow overview | ROUTER_MISROUTE |
| 3be0b556 | Alt season vague answer | ROUTER_MISROUTE |
| 4c2f656c | 除夕 general advice only | ROUTER_MISROUTE |
| 668df3df | GHO/AAVE incomplete analysis | ROUTER_MISROUTE |
| 7600a2a2 | Mining-to-AI lacked specifics | ROUTER_MISROUTE |
| 51113754 | Korean user, 5 complaints, truncated data | TOOL_DATA_ERROR |
| 494cdeb3 | Twitter future dates from truncation | TOOL_DATA_ERROR |
| e2717acb | Hottest projects data truncation | TOOL_DATA_ERROR |
| 1f57f856 | Korean → English response | LANGUAGE_DETECT_ERROR |
| bc0c8ec1 | SON token "doesn't exist" | LLM_HALLUCINATION |
| 229bfde0 | Decibel vault yields wrong | LLM_HALLUCINATION |

### Recommended Fixes (Priority Order)

1. **P0:** Tighten auto_router prompt for analytical queries → planner
2. **P0:** Add historical_price_data tool (query external.coingecko_hour)
3. **P0:** Add ATH/ATL fields to token_trading_data response
4. **P0:** Add self-consistency check for multi-turn sessions (see Pattern 6)
5. **P0:** Add input validation for execute_code (verify prices/dates match tool outputs before running generated code)
6. **P0:** Add output sanity check for execute_code (domain-specific: lower leverage = safer, not riskier)
7. **P1:** Fix language_detect for mixed CJK+English input
8. **P1:** Summarize truncated OHLC data instead of raw rows
9. **P1:** System prompt guardrail: "Only use numbers from tool outputs. If no tool provided a number, say so."
10. **P1:** Table label verification prompt (re-check ratings match directional logic)
11. **P1:** Use pre-built verified functions for common calculations (liquidation, drawdown, returns) instead of LLM-generated code

---

## Audit: Feb 18, 2026 — Session c91376f1 (HYPE Deep Dive)

**Type:** Proactive session audit (not from feedback pipeline)
**Session:** [c91376f1](https://us.cloud.langfuse.com/project/cm6vcb1bb0akyad074n1zh0nr/sessions/c91376f1-91b2-4995-97d6-76519498ff74)
**Messages:** 15 (all Chinese, all V2_THINKING — routing was correct)
**Topic:** HYPE (Hyperliquid) investment thesis, leverage risk, tokenomics

### New Patterns Discovered: `LLM_REASONING_ERROR` + `LLM_CODE_ERROR`

This session revealed two new failure modes not seen in the feedback pipeline audit:
1. **Correct numbers with wrong reasoning** — the AI labels wrong despite calculating right
2. **LLM-generated code with inverted logic** — `calculate_agent` wrote Python with `>` instead of `<`

### Issues Found

#### P0: Inverted leverage liquidation risk labels (CODE BUG)

| Leverage | Liq Price | AI Rating | Correct Rating | Error |
|---|---|---|---|---|
| 5x | $72,000 | 🟡 Close call | 🔴 **LIQUIDATED** (price hit $62.8k) | Understated |
| 3x | $60,000 | 🟢 Survived | 🟢 Barely survived | OK |
| 2x | $45,000 | 🔴 Wiped out | 🟢 **Survived easily** | Inverted |

**Root cause traced to execute_code:** After checking Langfuse observations, the full chain of failure was:
1. `team_planner` (gemini-3-flash) passed entry price $90,000 (actual was ~$97,000)
2. `calculate_agent` (grok-4-1-fast-reasoning) wrote Python with inverted comparison: `results1[f'{lev}x'] > 60000` (should be `<`)
3. `execute_code` ran the code successfully — no errors raised
4. `reporter_agent` partially re-interpreted but still got 2x wrong

This is `LLM_CODE_ERROR`, not just `LLM_REASONING_ERROR` — the bug was in generated code, not in text reasoning.

#### P0: Self-contradicting supply data within session

| Message | Circulating Supply | Total Supply |
|---|---|---|
| #5 | 383M (75.91%) | 504.5M |
| #7 | 238M | 1B |

61% discrepancy. Directly affects the $50B market cap target price ($131 vs $210).

#### Drawdown numbers wrong and swapped

| Asset | AI: "Feb crash" | Actual Feb crash | Error |
|---|---|---|---|
| BTC | 28.4% | **35.2%** | Understated by 7pp |
| ETH | 35.2% | **45.9%** | Understated by 11pp |
| SOL | 40.4% | **48.4%** | Understated by 8pp |

AI appears to have swapped "1011暴跌" numbers with the Feb 2026 crash numbers.

#### Other verified errors

| Claim | Actual | Error |
|---|---|---|
| HYPE 2025 low: $10.27 (Jan) | $9.54 (Apr 7) | Wrong month, wrong price |
| BTC crash: "from $90k" | From ~$97k | Understated starting price |
| HYPE price: $31.08 (Feb 17) | ~$29.6 | 5% overstated |

#### What was correct

- ETH/BTC ratio decline 0.036 → 0.030 — accurate
- ETH price ~$1,950 on Feb 16 — correct ($1,968-$1,997)
- SOL market cap ~$48B — correct
- HYPE Feb 11 low ~$28.81 — correct ($28.50 actual)
- All routing to V2_THINKING — correct for analytical queries

---

## Audit: Feb 18, 2026 — Session f18305ba (GPS Token Theft Forensics)

**Type:** Proactive session audit
**Session:** [f18305ba](https://us.cloud.langfuse.com/project/cm6vcb1bb0akyad074n1zh0nr/sessions/f18305ba-9753-42e2-a557-0d4002b1fc8b)
**Messages:** 2 substantive (Chinese, Message 1 V2_THINKING, Message 2 V2)
**Topic:** On-chain forensics — EVM address activity + GPS (GoPlus Security) token theft investigation

### New Pattern Discovered: `TOOL_PARAM_ERROR`

This session revealed a new failure mode: **the LLM called the right tool but with wrong parameters (wrong chain)**. The GPS token exists on Base chain, but the LLM sent the GPS-filtered query to Ethereum mainnet, producing a false negative.

### Issues Found

#### P0: False negative — "never held GPS" when 10,839 GPS were stolen

**Message 1:** User asked about GPS theft from address `0x8f5174...0ec577`.

AI confidently stated: "该地址从未持有过GPS代币" (this address NEVER held GPS tokens).

**Root causes (compound failure):**

| # | Root Cause | What happened |
|---|-----------|---------------|
| 1 | `TOOL_PARAM_ERROR` | `wallet_onchain_data` searched for GPS on Ethereum mainnet; GPS contract is on Base chain |
| 2 | `TOOL_DATA_ERROR` | DeBank `get_transaction_history` returned the theft tx but without token symbol/amount |
| 3 | `LLM_INTERPRETATION_ERROR` | AI had a Send to drainer address `0x00003fa9...` at the exact theft timestamp but didn't investigate |
| 4 | `LLM_HALLUCINATION` | AI claimed "multi-chain scan including Base" when GPS was only searched on Ethereum |

#### Message 2: Correct after user provided tx hash

User provided: tx hash `0xfc0a11c9...`, hacker address `0x00003fa9...180000`, time 2025-01-19 22:18:13.

`evm_onchain_agent` correctly verified on Base chain:
- `get_erc20_balance` at block 25,253,472 (pre-theft): **10,839.261232 GPS** ✅
- `get_erc20_balance` at block 25,253,474 (post-theft): **0 GPS** ✅
- `get_erc20_balance` of hacker at same block: **10,839.261232 GPS** ✅
- `get_erc20_token_info`: Confirmed GPS = GoPlus Security on Base ✅

### Source Tracing

| Claim | Source | Correct? |
|-------|--------|----------|
| "Never held GPS" (Msg 1) | `wallet_onchain_data` on Ethereum (wrong chain) | **WRONG** |
| "Multi-chain scan including Base" (Msg 1) | No GPS-specific tool call on Base | **HALLUCINATED** |
| SXT 400 → 0.032 ETH | `wallet_onchain_data` (Moralis) | Sourced |
| GPS stolen: 10,839.261232 (Msg 2) | `get_erc20_balance` at block 25253472 | **CORRECT** |
| Hacker received same amount (Msg 2) | `get_erc20_balance` of hacker | **CORRECT** |

### Key Takeaway

The evidence was there in Message 1 — DeBank returned a "Send" to the hacker address at the exact theft timestamp. But without token details in the DeBank response and with the GPS-specific search on the wrong chain, the AI had no way to connect the dots. The `evm_onchain_agent` (used in Message 2) had the right tools (`get_erc20_balance`, `get_evm_transaction_receipt`) but wasn't routed to in Message 1.

### Recommended Fixes (from this session)

1. **P0:** When `db_internal_data` returns a token's chain, force subsequent tool calls to that chain
2. **P0:** Add token symbol/amount to DeBank `get_transaction_history` response
3. **P0:** When user asks "was X stolen" and tools return 0 results, say "not found on chains checked" not "never happened"
4. **P1:** Route `evm_onchain_agent` earlier when query involves theft/transfer forensics
5. **P1:** Don't claim audit scope beyond what tools actually queried

---

## Audit: Feb 18, 2026 — Session 70742ee0 (OpenSea $SEA + 2025 TGE Performance)

**Type:** Proactive session audit
**Session:** [70742ee0](https://us.cloud.langfuse.com/project/cm6vcb1bb0akyad074n1zh0nr/sessions/70742ee0-6cb5-4e73-ab3c-60e8b8a6553d)
**Messages:** 3 (English, all V2 — should have been V2_THINKING)
**Topics:** OpenSea $SEA token analysis, 2025 TGE token performance comparison, Football.Fun (FUN) ICO verification

### New Pattern Discovered: `TOOL_PARAM_ERROR` sub-type 8b (Token Symbol Disambiguation)

This session revealed a cascading compound failure where each mistake enabled the next:
1. Tool returned data for the wrong token (FunFair instead of Football.Fun)
2. AI fabricated a calculation on that wrong data
3. AI contradicted itself when user corrected

### Issues Found

#### P0: Cascading compound failure — wrong token → hallucinated number → self-contradiction

**The full chain:**

| Step | Root Cause | What happened |
|---|---|---|
| 1 | `TOOL_PARAM_ERROR` (8b) | `token_trading_data` called with `entity: ['FUN']`, resolved to `coin_id: "funfair"` (FunFair, price $0.001) instead of Football.Fun (price $0.034). 8.5x price difference. |
| 2 | `LLM_HALLUCINATION` | AI claimed "Football.Fun (FUN) at +11.6% versus ICO" — no tool returned this number. Built on wrong-token data. |
| 3 | `LLM_REASONING_ERROR` (6b) | Message 2: "+11.6% above ICO". Message 3: user corrects → AI confirms ICO FDV $60M, current ~$34.7M = -43%. Direct self-contradiction, no acknowledgment. |
| 4 | `ROUTER_MISROUTE` | All 3 messages routed V2 instead of V2_THINKING. Analytical TGE comparison deserved deep planning. |

**Key evidence from Langfuse:**
- `token_trading_data` input: `{'entity': ['FUN'], 'filters': ['price']}`
- `token_trading_data` output: `{"coin_id":"funfair","symbol":"FUN","price_USD":0.001317...}`
- Football.Fun actual CoinGecko `coin_id`: `sport-fun`, price ~$0.034
- "+11.6%" figure: not found in any tool output → hallucinated
- `calculate_table_data` returned an error during trace 2 processing

#### P1: All 3 messages routed V2 instead of V2_THINKING

| Message | Query | Routing | Should be |
|---|---|---|---|
| #1 | "analyze opensea announcement and share if they are going to drop their $SEA token" | V2 | V2_THINKING |
| #2 | "which are the 15% of tokens in 2025 that have not [fallen below launch price]?" | V2 | V2_THINKING |
| #3 | "$fun ico price was at 60m FDV and its currently at 34M tho?" | V2 | V2_THINKING |

All three are analytical queries requiring multi-step research. V2 (direct agent) produced shallower analysis.

### What was correct

- Message 1 ($SEA token analysis): Well-sourced from `web_search`, `web_fetch`, `twitter_search`. Claims traced to PR Newswire, OpenSea Blog, CoinDesk, Dune Analytics.
- Message 3 (after user correction): Correctly verified via ICODrops, DexScreener, CryptoRank that ICO FDV = $60M, current FDV = ~$34.7M, total supply = 1B FUN.
- `recommend_data` returned a comprehensive list of 100+ TGE tokens — the tool itself worked correctly.

### Source Tracing

| Claim | Source | Correct? |
|---|---|---|
| $SEA 50% community allocation, Q1 2026 | `web_search` → PR Newswire | **CORRECT** |
| FUN price data (Message 2) | `token_trading_data` → `coin_id: funfair` | **WRONG TOKEN** |
| "+11.6% vs ICO" (Message 2) | No tool source found | **HALLUCINATED** |
| ICO FDV $60M (Message 3) | `search_agent` → ICODrops, PlayToEarn | **CORRECT** |
| Current FDV ~$34.7M (Message 3) | `search_agent` → DexScreener, CryptoRank | **CORRECT** |

### Key Takeaway

This session is the canonical example of a **cascading compound failure**. The initial tool error (wrong token) was silent — `token_trading_data` returned valid-looking data with `coin_id: "funfair"` visible in the output, but the AI never checked whether "funfair" matched "Football.Fun". That wrong data became the foundation for a fabricated calculation, which then self-contradicted when the user provided the real numbers. Each step compounded: wrong data → wrong math → wrong conclusion → loss of trust.

### Recommended Fixes (from this session)

1. **P0:** Validate `coin_id` in `token_trading_data` response against user's query context — "funfair" ≠ "Football.Fun"
2. **P0:** When `recommend_data` returns TGE tokens, include `coin_id` so subsequent tool calls use unambiguous identifiers
3. **P0:** Add price sanity check — if returned price is orders of magnitude different from context, flag disambiguation error
4. **P1:** Route analytical comparison queries (TGE performance, token screening) to V2_THINKING
5. **P1:** Cross-message self-consistency — when a new message contradicts a prior claim, acknowledge the correction explicitly
