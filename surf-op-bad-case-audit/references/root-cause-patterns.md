# Root Cause Patterns

Known failure patterns in the Surf AI pipeline, discovered through bad case audits. Each pattern includes detection criteria, verification steps, and fix recommendations.

**Core principle: Every number must have a source.** If a data claim in the AI response cannot be traced back to a tool call in the Langfuse observations, it's hallucinated. This applies to all patterns below — the first step is always: find the tool call that produced this number.

---

## Pattern 1: LLM Hallucinated Historical Data

**Root cause code:** `LLM_HALLUCINATION`
**Frequency:** ~33% of manual complaints (11/33 in Feb 18 audit); **79.8% of diver eval failures** (343/430 in Phase 2 Tier 1 eval); 97% of Phase 1 mining eval set; 42% of all faithfulness scores < 0.3 (14,324/33,988). The dominant failure mode at scale — most responses with faith=0 are pure LLM training memory with no tool sources. 99% of hallucinations are full fabrication (all claims unsupported).
**Severity:** P0

### How to detect

In the Langfuse trace:
1. `retriever_toolcall` calls `token_trading_data` → returns **current price only**
2. The reporter/planner LLM generates historical context (peak dates, ATH values, ratios, TVL, supply)
3. **There is no tool call that returned these historical numbers** — they come from LLM training memory

### What goes wrong

| AI generates | What's actually wrong |
|---|---|
| "SOL peaked at $X in {month}" | Peak date wrong by 2-8 months |
| "ETH ATH was $X in 2025" | ATH value off by up to 74% |
| "Token price was $X when {event} happened" | Uses price from wrong year |
| "TVL of $14B+" | 10x inflated hallucination |
| "Circulating supply of 588M" | Outdated by 120M+ tokens |
| "20x from 2022 low to 2025 peak" | Unverifiable multiplier |

### How to verify

```sql
-- Check actual ATH
SELECT max(price) as ath, argMax(hour, price) as ath_date
FROM external.coingecko_hour
WHERE symbol = '{TOKEN}' AND toYear(hour) = {YEAR}

-- Check actual price on a date
SELECT hour, price FROM external.coingecko_hour
WHERE symbol = '{TOKEN}'
  AND hour >= '{DATE} 00:00:00' AND hour <= '{DATE} 23:59:59'
ORDER BY hour LIMIT 5

-- Check ratio between tokens
SELECT avg(a.price / b.price) as avg_ratio
FROM external.coingecko_hour a
JOIN external.coingecko_hour b ON a.hour = b.hour AND b.symbol = 'BTC'
WHERE a.symbol = '{TOKEN}' AND toYear(a.hour) = {YEAR}
```

### Fix recommendations

1. **Add `historical_price_data` tool** — query `external.coingecko_hour` for historical prices
2. **Add ATH/ATL fields** to `token_trading_data` response — CoinGecko API provides `ath`, `ath_date`, `atl`, `atl_date`
3. **System prompt guardrail** — "If no tool provided historical data, say 'I don't have verified historical data for this'"

---

## Pattern 2: auto_router Misrouting to Shallow Flow

**Root cause code:** `ROUTER_MISROUTE`
**Frequency:** ~39% of manual complaints (13/33 in Feb 18 audit). Not directly measurable by faithfulness scoring or diver eval — routing errors reduce quality but may still produce sourced claims. Not captured in Phase 2 diver eval (0% of 430 failures). Requires dedicated routing quality metric to detect at scale.
**Severity:** P0

### How to detect

In the Langfuse trace:
1. Find the `auto_router` observation
2. Check its output: `{"selected_agent": "reporter_agent", "session_type": "V2_INSTANT"}`
3. The query was analytical/complex and should have gone to `planner` / `V2_THINKING`

### Query types that should route to planner but don't

| Query pattern | Why it needs planner |
|---|---|
| "Why does X..." / "How does X work..." | Requires multi-step reasoning |
| "Deep dive into X" / "详细分析" / "深入" | Explicitly asks for depth |
| "Compare X vs Y" | Needs multiple tool calls |
| "What's the outlook for X" | Needs news + data + synthesis |
| Multi-part questions | Each sub-question needs separate research |
| "When will X happen" (prediction) | Needs data gathering + reasoning |

### How to verify

Check the `auto_router` node in the trace:
- **Input:** the query + retriever context
- **Output:** `selected_agent` and `session_type`
- **Model:** deepseek-v3p1

Compare with a case where the same type of query was correctly routed to planner — the answer quality difference is dramatic.

### Fix recommendations

1. **Update `auto_router` system prompt** — add explicit routing rules for analytical queries
2. **Add complexity signal** — if query has >1 sub-question, force planner route
3. **Keyword triggers** — "why", "how", "deep dive", "compare", "分析", "详细" → planner

---

## Pattern 3: language_detect Mixed-Language Failure

**Root cause code:** `LANGUAGE_DETECT_ERROR`
**Frequency:** ~9% of complaints (3/33 in Feb 18 audit)
**Severity:** P1

### How to detect

In the Langfuse trace:
1. Find the `language_detect` observation
2. Check input (user's message) vs output (detected language)
3. If the message has mixed languages (e.g., Korean + English terms), the dominant character count wins

### Known triggers

- Korean text with English crypto terms: "최근 모나드 퇴사자 목록 • Head of Growth (Intern)"
- Chinese text with English project names: "bankr的NFT有什么作用？"
- Japanese text with English token symbols: "BTCの価格は..."

### Fix recommendations

1. **Session history fallback** — if prior messages were in language X, default to X
2. **Weight CJK characters higher** — a single CJK sentence should override English nouns
3. **Use app_language setting** as tiebreaker (but note: some users set app to English despite using CJK)

---

## Pattern 4: token_trading_data Truncation

**Root cause code:** `TOOL_DATA_ERROR`
**Frequency:** ~15% of manual complaints (5/33 in Feb 18 audit); **7.9% of diver eval failures** (34/430 in Phase 2 Tier 1 eval, mapped from `tool_failure` category)
**Severity:** P1

### How to detect

In the Langfuse trace:
1. Find the `token_trading_data` tool call
2. Check the output — look for "rows omitted" or truncated OHLC tables
3. The LLM treats truncated data as complete and draws conclusions from partial data

### What goes wrong

The tool returns paginated OHLC data like:
```
| date | open | high | low | close |
| 2026-02-01 | 82.1 | 84.3 | 81.0 | 83.5 |
| 2026-02-02 | 83.5 | 85.1 | 82.8 | 84.2 |
... (335 rows omitted) ...
| 2026-02-12 | 81.2 | 82.5 | 80.1 | 81.7 |
```

The LLM sees only the first and last few rows and extrapolates, sometimes generating wrong trends or future data points.

### Fix recommendations

1. **Return summary statistics** — min/max/avg/median instead of raw rows
2. **Add explicit warning** — "Data is partial — do not extrapolate trends"
3. **Pagination handling** — if data is truncated, summarize in the tool before returning to LLM

---

## Pattern 5: News/Search Returning Stale Results

**Root cause code:** `TOOL_DATA_ERROR`
**Frequency:** Occasional (observed in Feb 18 audit)
**Severity:** P1

### How to detect

In the trace, check `news_search` output timestamps. If articles are months old but presented as current context, the LLM may confuse timelines.

### Known example

User asked about current events on Feb 12, 2026. The news tool returned articles from March-April 2025 as the top results. User complained: "现在是2026年2月12！！" (It's February 12, 2026!!)

### Fix recommendations

1. **Add recency bias** to news search — weight recent articles higher
2. **Include date in tool output** prominently so LLM can contextualize
3. **System prompt** — "Always check article dates. If news is >30 days old, note this to the user"

---

## Pattern 6: LLM Reasoning Errors (Correct Numbers, Wrong Logic)

**Root cause code:** `LLM_REASONING_ERROR`
**Frequency:** Observed in multi-turn analytical sessions (Session c91376f1)
**Severity:** P0

### How to detect

Unlike hallucination (wrong numbers) or interpretation errors (misusing tool data), reasoning errors produce **correct calculations with wrong conclusions**. The numbers pass a spot-check but the logic is inverted.

**Check for these sub-patterns:**

#### 6a. Inverted risk/rating labels

The AI builds a table with correct math but assigns status labels to the wrong rows.

**Canonical example — leverage liquidation (Session c91376f1):**
- Entry: $90,000 BTC. Actual crash low: $62,822.
- 5x leverage → liq at $72,000 → price went BELOW $72k → **LIQUIDATED**
- 2x leverage → liq at $45,000 → price never near $45k → **SURVIVED**
- AI labeled 5x as "close call 🟡" and 2x as "wiped out 🔴" — **completely inverted**

**Detection method:** For any table with a rating/status column, verify that the ratings are consistent with the numbers. Specifically:
- Lower leverage → lower liq price → more room to fall → SAFER
- Higher drawdown → WORSE performance
- Lower volatility → LOWER risk
- If these directional relationships are violated, flag `LLM_REASONING_ERROR`

#### 6b. Self-contradicting data across messages

The AI gives different values for the same metric in different messages within one session.

**Canonical example — HYPE supply (Session c91376f1):**
- Message 5: circulating supply = 383M, total supply = 504.5M
- Message 7: circulating supply = 238M, max supply = 1B
- 61% discrepancy — directly affects the $50B market cap calculation the user was asking about

**Detection method:** Extract key metrics (supply, market cap, price, ratios) from every message in a multi-turn session. Flag any metric that changes by >10% between messages without an explicit correction.

#### 6c. Conclusion contradicts its own data

The AI presents data in a table, then draws a conclusion that doesn't follow from the data shown.

**Examples:**
- Table shows 35.2% drawdown, text says "28.4% drawdown"
- Table shows Asset A outperforms Asset B, conclusion recommends Asset B
- Probability model says <10% chance, but advice assumes it will happen

**Detection method:** Compare the narrative text against any tables/data in the same message. The conclusion should logically follow from the data presented.

### Why this is P0

Reasoning errors are more dangerous than wrong numbers because:
1. **They look authoritative** — correct math builds false confidence
2. **They invert advice** — telling users low leverage is MORE dangerous than high leverage
3. **They're hard to catch** — numerical verification passes, only logical review catches them
4. **Financial impact** — a user acting on inverted risk guidance could make catastrophically wrong decisions

### Fix recommendations

1. **P0: Add self-consistency check** — In multi-turn sessions, compare key metrics across messages and flag contradictions before responding
2. **P1: Table verification prompt** — After generating a table with ratings, instruct the LLM to re-verify that labels match the directional logic of the numbers
3. **P1: Eval harness for reasoning** — Build test cases with known liquidation/risk scenarios where the correct label ordering is known, test that the LLM assigns them correctly

---

## Pattern 7: LLM-Generated Code with Bugs

**Root cause code:** `LLM_CODE_ERROR`
**Frequency:** Observed in analytical sessions using `calculate_agent` (Session c91376f1)
**Severity:** P0

### How to detect

In the Langfuse trace:
1. Find the `calculate_agent` observation
2. It calls the `execute_code` tool with LLM-generated Python code
3. The code **runs successfully** (no errors) but produces wrong results
4. The bug is in the code logic, not in execution

**Key insight:** Code execution succeeding does NOT mean the code is correct. The LLM can write syntactically valid code with inverted logic.

### What goes wrong

The LLM generates code where:
- **Comparisons are inverted** (`>` instead of `<`, or vice versa)
- **Input values are wrong** (upstream LLM passed incorrect parameters)
- **Formulas are wrong** (wrong calculation logic)
- **Variable labels are swapped** (assigning results to wrong categories)

### Canonical example — leverage liquidation (Session c91376f1)

**The full chain of failure:**

1. `team_planner` (gemini-3-flash) passed **wrong entry price** ($90,000 instead of actual ~$97,000)
2. `calculate_agent` (grok-4-1-fast-reasoning) generated Python code:
   ```python
   entry = 90000  # WRONG: actual was ~97000
   leverages = [5, 3, 2]
   results1 = {f'{lev}x': liquidation_price(entry, lev) for lev in leverages}
   # BUG: comparison is inverted
   survival_60k = {
       lev: '存活' if results1[f'{lev}x'] > 60000 else '爆仓'
       for lev in leverages
   }
   ```
3. The comparison `> 60000` means "if liquidation price is ABOVE crash low, survived" — this is **backwards**. A liq price above the crash low means the price fell PAST your liq point → you were liquidated.
4. `execute_code` ran the code — **no errors**, returned results
5. `reporter_agent` (deepseek-v3p1) received the wrong results and **partially re-interpreted** them but still got the 2x leverage rating wrong

**Result:** User was told 2x leverage would "wipe out" when it actually survived easily.

### How to audit execute_code calls

```sql
-- Find execute_code calls in a trace
SELECT
    id, name, type, start_time,
    substring(input, 1, 2000) as code_input,
    substring(output, 1, 2000) as code_output
FROM default.langfuse_observations
WHERE trace_id = '{trace_id}'
  AND name = 'execute_code'
ORDER BY start_time
```

**For each execute_code call, check:**
1. Read the actual Python code in the `input` field
2. Verify all comparisons (`>`, `<`, `>=`, `<=`) go the right direction
3. Verify input values match reality (entry prices, dates, thresholds)
4. Verify output labels match the directional logic of the calculation
5. If the code uses conditional logic, trace through it manually with known values

### Why this is P0

1. **Silent failure** — code runs without errors, so no error signals are raised
2. **Looks computed** — users trust "calculated" results more than LLM-generated text
3. **Compounds errors** — wrong inputs from upstream + wrong code logic = double inversion that's hard to trace
4. **Multi-agent blame diffusion** — the error spans team_planner → calculate_agent → execute_code → reporter, so no single node "owns" the bug

### Fix recommendations

1. **P0: Input validation for execute_code** — Before running generated code, verify that input values (prices, dates) match what the tools actually returned
2. **P0: Output sanity check** — After code execution, apply domain-specific checks (e.g., lower leverage should be safer, not riskier)
3. **P1: Code review prompt** — Instruct calculate_agent to re-read its own code and verify comparison directions before submitting to execute_code
4. **P1: Deterministic alternatives** — For common calculations (liquidation price, drawdown, returns), use pre-built verified functions instead of LLM-generated code

---

## Pattern 8: Tool Called with Wrong Parameters

**Root cause code:** `TOOL_PARAM_ERROR`
**Frequency:** **8.6% of diver eval failures** (37/430 in Phase 2 Tier 1 eval, mapped from `retrieval_failure` category). Also observed in on-chain forensics (Session f18305ba) and TGE analysis (Session 70742ee0)
**Severity:** P0

`TOOL_PARAM_ERROR` has two known sub-types:
- **8a: Chain mismatch** — right tool, wrong blockchain network
- **8b: Token symbol disambiguation** — right tool, wrong token (ambiguous ticker resolves to wrong project)

Both produce the same dangerous outcome: the tool returns valid-looking data for the wrong target, and the LLM treats it as definitive.

### How to detect

In the Langfuse trace:
1. Find the tool call (e.g., `wallet_onchain_data`, `token_trading_data`)
2. Check the **input parameters** — specifically `chain`, `chain_id`, `entity`, token contract address, date filters
3. Compare against known facts:
   - If `db_internal_data` says the token is on Base, but the tool call targets Ethereum mainnet → **8a: chain mismatch**
   - If the user is discussing "Football.Fun (FUN)" but `token_trading_data` returns `coin_id: "funfair"` → **8b: token disambiguation**
4. The tool returns valid-looking results — technically correct for the wrong target, but useless or misleading for the user's actual question

**Key insight:** The tool isn't broken — the LLM sent it to the wrong target. The result is either a **false negative** (chain mismatch: 0 results) or **false data** (token disambiguation: real data for the wrong token) that the LLM treats as definitive.

### What goes wrong

| LLM does | What's wrong | Sub-type | Result |
|----------|-------------|----------|--------|
| Searches GPS on Ethereum mainnet | GPS contract is on Base chain | 8a | 0 transfers found (false negative) |
| Queries `token_trading_data` for "FUN" | Returns FunFair (`coin_id: funfair`) instead of Football.Fun | 8b | Wrong token's price data used silently |
| Queries wallet history for date range X | Relevant event happened outside that range | 8a | Event not found |
| Filters by token symbol string | Same symbol maps to multiple tokens | 8b | Wrong token's data |
| Queries address on single chain | User's activity spans multiple chains | 8a | Incomplete picture |

### 8a: Chain mismatch — GPS token theft (Session f18305ba)

**User asked:** Is GPS stolen from address `0x8f5174...0ec577`? When, how much, where did it go?

**What happened:**

1. `db_internal_data` returned GPS token info including **Base chain** contract `0x0C1dC73159e30c4b06170F2593D3118968a0DCa5` ✅
2. `wallet_onchain_data` was called with GPS filter — but searched **Ethereum mainnet** (`chain: "evm"`) instead of Base
3. Result: `"filtered_transfers": 0` — LLM concluded "this address never held GPS"
4. Meanwhile, DeBank `get_transaction_history` on Base DID return a suspicious transfer:
   - Time: 1737296293 (= 2025-01-19 14:18:13 UTC)
   - Category: "Send"
   - To: `0x00003fa9a87b12acba277322c3913606f3180000` (the hacker)
   - **But no token symbol or amount** — DeBank strips token details from this endpoint
5. The AI had the theft record but couldn't identify it as GPS because the token info was missing
6. AI confidently stated: "该地址从未持有过GPS代币" (this address NEVER held GPS)

**After user corrected with the tx hash (Message 2):**
- `evm_onchain_agent` searched Base chain correctly
- `get_erc20_balance` at block 25,253,472 (pre-theft): **10,839.261232 GPS**
- `get_erc20_balance` at block 25,253,474 (post-theft): **0 GPS**
- `get_erc20_balance` of hacker at block 25,253,474: **10,839.261232 GPS**
- All confirmed on Base chain (chain_id: 8453)

### Compound failure: TOOL_PARAM_ERROR + TOOL_DATA_ERROR + LLM_INTERPRETATION_ERROR

This session shows how multiple small failures compound into a confident wrong answer:

1. **`TOOL_PARAM_ERROR`:** GPS-specific search queried wrong chain (Ethereum instead of Base)
2. **`TOOL_DATA_ERROR`:** DeBank returned the theft transaction but without token symbol/amount
3. **`LLM_INTERPRETATION_ERROR`:** AI had a suspicious Send to a drainer address at a relevant time but didn't investigate further
4. **`LLM_HALLUCINATION`:** AI claimed "multi-chain scan including Base" when GPS was only searched on Ethereum

Each error alone might not cause a wrong answer. Together, they produced a false negative that directly contradicted the user's experience.

### 8b: Token symbol disambiguation — FUN/FunFair confusion (Session 70742ee0)

**User asked:** Which 2025 TGE tokens haven't fallen below launch price? (then followed up about Football.Fun's $FUN)

**What happened — a cascading compound failure:**

```
Step 1: TOOL_PARAM_ERROR (token disambiguation)
  └─ token_trading_data called with entity: ['FUN']
  └─ Tool resolved 'FUN' to coin_id: "funfair" (FunFair, price ~$0.004)
  └─ Actual target: Football.Fun (sport-fun on CoinGecko, price ~$0.034)
  └─ Price difference: 8.5x — completely different token
  └─ The AI never noticed: "funfair" was in the tool output but never surfaced to the user

Step 2: LLM_HALLUCINATION (fabricated calculation)
  └─ AI claimed "Football.Fun (FUN) at +11.6% versus ICO"
  └─ No tool returned "+11.6%" — this number has no source
  └─ Built on wrong-token data from Step 1

Step 3: LLM_REASONING_ERROR (cross-message self-contradiction)
  └─ Message 2: "FUN is +11.6% above ICO price"
  └─ Message 3: User corrects → AI verifies ICO FDV $60M, current ~$34.7M = -43%
  └─ The AI contradicted its own prior claim without acknowledging it

Step 4: ROUTER_MISROUTE (compounding factor)
  └─ All 3 messages routed V2 instead of V2_THINKING
  └─ Analytical TGE comparison query deserved deep planning
```

**Each step enabled the next:** wrong token data → no valid basis for calculation → hallucinated number → self-contradiction when user corrected. If any single step had been caught, the cascade would have stopped.

**Key evidence from Langfuse:**
- `token_trading_data` input: `{'entity': ['FUN'], 'filters': ['price']}`
- `token_trading_data` output: `{"coin_id":"funfair","symbol":"FUN","price_USD":0.001317...}`
- Football.Fun actual price on CoinGecko (sport-fun): ~$0.034
- AI's response: "+11.6% vs ICO" — not found in any tool output

**After user correction (Message 3):**
- `search_agent` correctly found via ICODrops, DexScreener, CryptoRank: ICO FDV = $60M, current FDV = ~$34.7M
- The AI acknowledged -43% drop — directly contradicting its own "+11.6%" from the previous message

### How to audit tool parameters

```sql
-- Find all tool calls and their inputs
SELECT
    name,
    substring(toString(input), 1, 500) as input_params,
    substring(toString(output), 1, 300) as output_preview
FROM default.langfuse_observations
WHERE trace_id = '{trace_id}'
  AND type = 'TOOL'
ORDER BY start_time
```

**For each tool call, check:**
1. If querying on-chain data: does the `chain` parameter match where the token/contract lives?
2. If filtering by token: does the filter use the correct contract address for that chain?
3. If querying by date range: does the range cover the relevant time period?
4. If a tool returns 0 results: is it genuinely empty, or was it asked about the wrong target?
5. If `token_trading_data` returns data: does the `coin_id` in the response match the token the user is discussing? (e.g., `funfair` vs `sport-fun`)
6. If the returned price is orders of magnitude different from context: the tool probably resolved to the wrong token

### Why this is P0

1. **False negatives are worse than errors** — telling a user "your tokens were never stolen" when they were is a trust-destroying response (8a)
2. **Silent wrong-token data is worse than no data** — the AI builds analysis on a completely different token's price without noticing (8b)
3. **The AI sounds confident** — empty tool results + LLM memory = "I thoroughly checked and found nothing"
4. **Cascading failures** — wrong data from Step 1 enables hallucinated calculations in Step 2, which self-contradict in Step 3
5. **Fabricated methodology** — the AI may describe a scope broader than what tools actually queried
6. **Multi-chain is default** — most users have activity across multiple EVM chains; single-chain queries are almost always insufficient

### Fix recommendations

**For 8a (chain mismatch):**
1. **P0: Chain propagation** — When `db_internal_data` or `retriever` identifies a token's chain, propagate that to all subsequent tool calls. If GPS is on Base, force Base-chain queries.
2. **P0: Cross-chain fallback** — If a token-specific query returns 0 results on one chain, automatically retry on other chains where the token contract exists.
3. **P0: Flag false negatives** — If user asks "was X stolen" and tools find 0 results, the response should say "I could not find evidence on the chains I checked" instead of "X was never stolen."
4. **P1: DeBank token details** — Ensure `get_transaction_history` returns token symbol and amount for transfers, not just "Send" with gas fees.
5. **P1: Route to `evm_onchain_agent` for forensics** — When the query involves theft, transfers, or contract interactions, route to `evm_onchain_agent` which has `get_erc20_balance` and `get_evm_transaction_receipt` — the tools that actually solved it in Message 2.

**For 8b (token symbol disambiguation):**
1. **P0: Validate `coin_id` in tool response** — When `token_trading_data` returns data, the AI should check that the `coin_id` (e.g., "funfair") matches the token the user is discussing (e.g., "Football.Fun"). If they don't match, retry with a more specific identifier.
2. **P0: Use `coin_id` from `recommend_data`** — When `recommend_data` returns a TGE list with token symbols, include `coin_id` so subsequent `token_trading_data` calls use unambiguous identifiers.
3. **P0: Price sanity check** — If the returned price is orders of magnitude different from what context suggests (e.g., $0.001 vs $0.034), flag it as a possible disambiguation error.
4. **P1: Return full token name** — `token_trading_data` should prominently return the full project name alongside `coin_id` so the LLM can cross-check against user context.

---

## Pattern 9: LLM Misinterprets Tool Output

**Root cause code:** `LLM_INTERPRETATION_ERROR`
**Frequency:** Observed as a compounding factor in GPS theft investigation (Session f18305ba) and in multi-step analytical sessions. Often co-occurs with `TOOL_PARAM_ERROR` or `TOOL_DATA_ERROR` — the tool returns partial/ambiguous data and the LLM draws wrong conclusions from it.
**Severity:** P1

### How to detect

In the Langfuse trace:
1. Find a tool call that returned **correct or partially correct data**
2. Read the LLM's response — it either **ignores** relevant data in the tool output or **misreads** what the tool returned
3. The failure isn't in the tool (it returned what it should) or in the LLM's knowledge (it's not hallucinating) — it's in the LLM's use of the tool output

### What goes wrong

| Tool returns | LLM does | What went wrong |
|---|---|---|
| Suspicious "Send" tx to known drainer address | Ignores it, says "no theft found" | Failed to connect context clues |
| Price data with timestamps | Uses wrong timestamp's price for the claim | Picked wrong row from tool output |
| Multi-field JSON with nested data | Extracts wrong field or wrong nesting level | Structural misread of output format |
| Partial data (some fields missing) | Treats missing fields as "confirmed absent" | Absence of evidence ≠ evidence of absence |
| Tool output with units or denomination | Misreads units (wei vs ETH, satoshi vs BTC) | Unit conversion error |

### Canonical example — GPS theft (Session f18305ba)

The compound failure in the GPS session includes a clear `LLM_INTERPRETATION_ERROR`:

1. DeBank's `get_transaction_history` on Base returned a transaction:
   - Time: 1737296293 (= 2025-01-19 14:18:13 UTC)
   - Category: "Send"
   - To: `0x00003fa9a87b12acba277322c3913606f3180000` (known drainer pattern)
   - **But no token symbol or amount** (DeBank strips token details from this endpoint)

2. The AI **had this data** in its context but failed to investigate further:
   - The "Send" to a drainer address at the time the user claimed theft → highly suspicious
   - Should have triggered a follow-up `get_erc20_balance` check
   - Instead, the AI concluded "该地址从未持有过GPS代币" (this address never held GPS)

3. The interpretation failure: treating **partial tool data** as **complete negative evidence**

### How to audit for interpretation errors

```sql
-- Find tool calls and the LLM generation that followed
SELECT
    o1.name as tool_name,
    substring(o1.output, 1, 500) as tool_output,
    o2.name as llm_name,
    substring(o2.output, 1, 500) as llm_response
FROM default.langfuse_observations o1
JOIN default.langfuse_observations o2
    ON o1.trace_id = o2.trace_id
    AND o2.start_time > o1.start_time
    AND o2.type = 'GENERATION'
WHERE o1.trace_id = '{trace_id}'
  AND o1.type = 'TOOL'
ORDER BY o1.start_time
LIMIT 20
```

**For each tool→LLM pair, check:**
1. Did the LLM reference all relevant data points from the tool output?
2. Did the LLM correctly interpret what the data means?
3. Did the LLM treat missing/absent data correctly? (missing ≠ "doesn't exist")
4. Did the LLM handle edge cases in the tool output (empty arrays, null fields, truncated data)?

### Distinguishing from other root causes

| If the problem is... | Root cause |
|---|---|
| Tool returned wrong data | `TOOL_DATA_ERROR` |
| Tool was called with wrong params | `TOOL_PARAM_ERROR` |
| LLM fabricated data with no tool source | `LLM_HALLUCINATION` |
| Tool returned correct data, LLM misused it | `LLM_INTERPRETATION_ERROR` |
| Tool returned correct data, LLM reasoned incorrectly | `LLM_REASONING_ERROR` |

The key distinction: `LLM_INTERPRETATION_ERROR` is about **reading the tool output wrong**, while `LLM_REASONING_ERROR` is about **drawing wrong conclusions from correctly-read data**.

### Fix recommendations

1. **P0: Structured output parsing** — When tools return complex JSON, have the LLM explicitly extract and list key fields before reasoning about them
2. **P0: Absence acknowledgment** — System prompt: "If a tool returns partial data (missing fields, empty arrays), state what is missing rather than treating it as negative evidence"
3. **P1: Follow-up trigger** — If a tool returns a suspicious but incomplete result (e.g., a "Send" to a drainer with no amount), automatically trigger a follow-up tool call for details
4. **P1: Unit verification** — For financial data, require explicit unit conversion steps (wei→ETH, satoshi→BTC) in the response

---

## Pattern 10: Cascading Hallucination from Conversation History

**Root cause code:** `LLM_HALLUCINATION`
**Frequency:** Observed in multi-turn sessions (Trace `47af240a`)
**Severity:** P0

### How to detect

In the Langfuse trace:
1. Session has multiple messages (messages_count > 3)
2. Earlier turns contain fabricated data (Uniswap v4 metrics, specific market caps, etc.)
3. Current turn's response references those earlier fabricated numbers as if they were established facts
4. The current turn's tool call returned different/tangential data

### What goes wrong

| Step | What happens |
|---|---|
| Turn 1-5 | Earlier responses contain hallucinated numbers (e.g., "$57.3M Ethereum fees", "83.8% market share") |
| Turn 6 | New query triggers `news_search` → returns tangential results |
| Reporter | Sees conversation history WITH the fabricated numbers + new tool data |
| Output | Mixes new (tangential) tool data with old (fabricated) history numbers |

### Why this is P0

Conversation history is treated as ground truth by the reporter. Once a hallucination enters the session, it persists and compounds across all subsequent turns.

### Fix recommendations

1. **P0: Tag tool-sourced vs unsourced data** — In conversation history, mark claims that came from tool calls vs claims generated by the LLM
2. **P1: Session-level fact tracking** — Track key metrics (prices, market caps, supply) across messages and flag contradictions
3. **P1: History compression** — When compressing conversation history, drop specific numbers and keep only the qualitative conclusions

---

## Pattern 11: Retriever PASS → Zero Tools → Complete Fabrication

**Root cause code:** `LLM_HALLUCINATION`
**Frequency:** Observed in conceptual/technical queries (Traces `3dc2b9b4`, `016ef86c`)
**Severity:** P0

### How to detect

In the Langfuse trace:
1. `retriever_toolcall` output is `"PASS"` — no tools called
2. Only pre-fetched context exists (Dune dashboards, generic entity data)
3. The reporter generates a detailed response with specific numbers, despite having no tool data

### What goes wrong

The retriever (XAI/Grok) decides the question doesn't need tools — perhaps because it's conceptual ("What's the ideal seed word for a VR platform?") or because it misjudges the technical depth needed ("Solana oracle network optimization"). The reporter then receives zero tool data and fabricates from parametric knowledge.

### Distinguishing correct PASS from incorrect PASS

| Query type | Correct decision |
|---|---|
| "What is DeFi?" (definition) | PASS is OK — general knowledge suffices |
| "Hi, thanks!" (greeting) | PASS is correct |
| "Optimize Solana oracle throughput" (technical) | PASS is WRONG — needs tool data for specific metrics |
| "Compare X vs Y with current data" (analytical) | PASS is WRONG — needs fresh data |

### Fix recommendations

1. **P0: Inject no-data warning** — When retriever returns PASS and query is not a greeting, add an explicit message to the reporter: "⚠️ NO TOOLS WERE CALLED. Only use conceptual knowledge."
2. **P1: PASS decision audit** — Log all PASS decisions with the query for periodic review of retriever decision quality

---

## Pattern 12: Thinking Tag Leaks in Output

**Root cause code:** `ROUTER_MISROUTE` (structural quality issue)
**Frequency:** 4 out of 5 sampled hallucination traces; systematic in all DeepSeek-reporter flows
**Severity:** P0

### How to detect

In the response:
1. Look for `<think>...</think>` or `<thinking>...</thinking>` blocks in the user-visible output
2. Look for internal tool references: `surf_faq`, `language_detect_01`, `image_content_01`, `retriever_toolcall`
3. Look for model reasoning about "what tools were called" or "what data is available"

In the Langfuse trace:
1. `FireworksDeepSeekChatModel` output has `type: "thinking"` content blocks
2. These blocks are passed through to the final response without sanitization

### What goes wrong

DeepSeek models emit `<think>` tags for internal reasoning. The `_ThinkSegmenter` in `fireworks_deepseek_chat_model.py` correctly parses these into separate content blocks, but:
- `simple_react_agent.py` adds `<thinking>` tags to content directly
- No sanitization step removes thinking content before the response reaches the user
- The reporter prompt has no instruction to strip thinking tags

### Fix recommendation

1. **P0: Add `strip_thinking_from_output()` in the response pipeline** — Remove all `<think>`, `</think>`, `<thinking>`, `</thinking>` blocks before sending to user. This is a simple regex filter applied at the SSE streaming layer.

---

## Pattern 13: Multimodal Model Stale Year Assumption

**Root cause code:** `LLM_INTERPRETATION_ERROR`
**Frequency:** Observed in image analysis queries (Trace `3afde82e`)
**Severity:** P2

### How to detect

In the Langfuse trace:
1. `ChatGoogleGenerativeAI` (Gemini) is called for image analysis
2. Gemini's output references the "current year" as 2024 instead of 2026
3. Gemini flags dates in the image (e.g., "2026-01-22") as "future dates"
4. Reporter receives conflicting year references: Gemini says 2024, system says 2026

### What goes wrong

Gemini's training cutoff makes it assume the current year is 2024. When analyzing images that contain 2026 dates, Gemini flags them as impossible future data. The reporter model then gets confused about which year is correct.

### Fix recommendation

1. **P1: Pass `current_time` to Gemini** — Include "Current date is 2026-02-XX" in the Gemini prompt for image analysis
2. **P2: Time context validation** — If any model's output contradicts the system-provided `current_time`, prefer the system time

---

## Pattern 14: Empty Data Passed Through Without Warning (Systemic)

**Root cause code:** `LLM_HALLUCINATION` (root architectural cause)
**Frequency:** Systemic — affects all flows where tools return empty data
**Severity:** P0

### How to detect

This is the **systemic root cause** behind most LLM_HALLUCINATION failures. In the code:

1. `dataframe_markdown.py:17-18`: `if df.empty: return ""` — returns empty string, no warning
2. `model.py to_prompt()`: empty table becomes `[Empty Result]` — not flagged as an error
3. `agent_team_v2.py:74`: Reporter is told "Work with whatever data is available — do NOT request additional data retrieval"
4. `v2_reporter.md:11`: Reporter is told "If data appears insufficient, proceed with analysis"

### The cascade

```
Tool returns empty data
  → `dataframe_to_markdown_preview` returns ""
  → `to_prompt()` converts to "[Empty Result]"
  → Reporter sees [Empty Result] (not flagged as error)
  → Reporter is instructed to "proceed with analysis"
  → Reporter is told "do NOT request additional data"
  → Reporter fabricates from parametric knowledge
  → User sees authoritative-looking analysis built on nothing
```

### Fix recommendations

See `data/eval_set/odin_flow_fix_recommendations.md` Fix 1 for detailed code changes.

1. **P0: Change `dataframe_markdown.py`** — Return "⚠️ NO DATA RETURNED" instead of empty string
2. **P0: Change `model.py to_prompt()`** — Add explicit "Do NOT fabricate data" warning for empty tables
3. **P0: Change `agent_team_v2.py` line 74** — Replace "work with whatever data" with "if no tool data, say so"
4. **P0: Change `v2_reporter.md` line 11** — Replace "proceed with analysis" with "stop and acknowledge gap"

---

## Pattern 15: Eval False Positives

**Root cause code:** N/A (eval pipeline issue, not odin-flow)
**Frequency:** 1 out of 5 sampled hallucination traces was a false positive
**Severity:** P2

### How to detect

Compare the eval's `failure_detail` against the actual tool output:
1. Eval says "No tools were called" but trace shows tool calls DID exist
2. Eval says "fabricated future data" but the dates are the current year (2026)
3. Eval says N unsupported claims but the claims actually match tool output data
4. Eval struggles with non-English responses (Korean, Chinese)

### Known false positive case

Trace `e9760404` (PEPE chart in Korean):
- `token_trading_data` returned 7 days of valid OHLC data
- Model correctly computed daily percentage changes from the data
- Eval scored 45/45 claims as unsupported — likely because it couldn't match Korean text to English tool output

### Fix recommendations

1. **P1: Add "2026 is current year" to eval prompt** — Prevents evaluator from flagging 2026 dates as "future"
2. **P1: Two-pass eval** — First check if tools returned data; if yes, cross-reference claims against tool output before marking unsupported
3. **P2: CJK-aware eval** — Ensure the evaluator can match claims across languages (e.g., Korean text referencing English tool data)

---

## Pattern 16: Mixed-Truth Hallucination (Temporal Context Shift)

**Root cause code:** `LLM_HALLUCINATION`
**Severity:** Critical — hardest hallucination pattern to detect automatically
**First seen:** Session `04346294` (Feb 19, 2026)

### What happens

The AI produces a response where most facts are verifiably correct, but the temporal context is shifted — typically by exactly ±1 year. This creates a "mostly-true" response that passes naive fact-checks.

### Detection criteria

- AI cites a specific event with a date that is exactly 1 year off
- AI claims an event is "most recent" or "latest" when it was actually earlier in a sequence
- The entity, numbers, and relationship are all real — only the time/ordering is wrong
- No Langfuse traces / no tool calls (pure parametric knowledge)

### Example: Session 04346294

```
User: "did buildpad recently do any sale"
AI: "Most recent sale was Solayer (~Jan 17, 2026, $10.5M, $0.35/token)"

Verified reality:
- Buidlpad: REAL platform ✅
- Solayer sold on Buidlpad: REAL relationship ✅
- $10.5M at $0.35/token: REAL numbers ✅
- January 17, 2026: WRONG — was January 16, 2025 (off by 1 year) ❌
- "Most recent": WRONG — was the FIRST sale, 3+ later sales occurred ❌
```

### Why this is dangerous

1. **Passes numerical verification** — all numbers check out individually
2. **Passes entity verification** — the platform and project both exist
3. **Passes relationship verification** — Solayer DID sell on Buidlpad
4. **Only fails temporal verification** — requires knowing the chronological order of all events
5. **Users may not catch it** — the response reads as authoritative and specific

### How to detect

```
For each event/date claim:
1. Web search: "[entity] [event] [year-1] OR [year] OR [year+1]"
   → Check if the event happened in a different year
2. Recency check: "[entity] all [events]" or "[entity] history"
   → Build full timeline, verify "most recent" / "first" / "latest"
3. Cross-reference multiple sources (CryptoRank, The Block, project blog)
```

### Fix recommendations

1. **P0: Web search grounding for event claims** — When AI cites specific events/dates without tool data, trigger a web search to verify
2. **P0: "Most recent" / "latest" claims require chronological verification** — Must verify the full sequence, not just the cited event
3. **P1: +1/-1 year sanity check** — When training-cutoff dates appear, check if the event is being shifted to the current year
4. **P1: Confidence disclaimer for parametric knowledge** — When no tools were called, add "based on training data, may be outdated" caveat
