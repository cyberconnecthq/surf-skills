# Trace Analysis Skill - Human Documentation

Technical documentation for human reference. For Claude's workflow instructions, see SKILL.md.

## Overview

```
Langfuse API  →  fetch_trace.py  →  Local Files  →  Claude (Grep/Read)  →  Answer
```

## Commands

### Single Trace

```bash
# Fetch a trace (uses cache if exists)
python fetch_trace.py <trace_id>

# Fast mode (2x faster, 24x smaller)
python fetch_trace.py <trace_id> --fast

# Force re-fetch (ignore cache)
python fetch_trace.py <trace_id> --force
```

### Session (Multiple Traces)

```bash
# Fetch all traces in a session
python fetch_trace.py --session <session_id>

# Fast mode (recommended for sessions)
python fetch_trace.py --session <session_id> --fast

# Force re-fetch
python fetch_trace.py --session <session_id> --force
```

### Cache Management

```bash
# List cached traces
python fetch_trace.py --list

# Clean old traces
python fetch_trace.py --clean [days]

# Delete all traces
python fetch_trace.py --clean-all
```

## Performance Modes

| Mode | Time | Disk | Use Case |
|------|------|------|----------|
| **Cached** | instant | - | Repeated questions on same trace |
| **--fast** | ~5s | ~400KB | Quick triage, cost analysis |
| **Full** | ~10s | ~9MB | Deep dive, full content needed |

### What `--fast` Mode Skips

Skips writing individual observation files in `observations/` folder:

| Skipped Files | Description |
|---------------|-------------|
| `001_<name>.json` | Full observation metadata (timestamps, parent IDs) |
| `001_<name>_input.txt` | Complete observation input |
| `001_<name>_output.txt` | Complete observation output |

For 48 observations = **144 files skipped**.

### What `--fast` Mode Keeps

| File | Contains | Truncation |
|------|----------|------------|
| `all_outputs.txt` | Concatenated I/O | 5KB per observation |
| `tools_only.txt` | Tool calls summary | 500 chars per tool |
| `llm_only.txt` | LLM outputs | 800 chars per LLM |
| `key_values.txt` | Indexed numbers/addresses | Full (from visible content) |
| `call_tree.txt` | Execution hierarchy | Full |
| `cost_summary.txt` | Token/cost breakdown | Full |

### Questions `--fast` Cannot Answer

| Question Type | Why It Fails | Example |
|---------------|--------------|---------|
| Full content retrieval | Output truncated at 5KB | "Show complete HTML from web_fetch" |
| Values in truncated section | Only indexes visible content | Values after 5KB mark missing |
| Complete LLM prompts | Input truncated at 5KB | "What was the full system prompt?" |
| Exact timestamps | JSON metadata not saved | "Precise start_time of observation #23?" |
| Parent-child IDs | Only in JSON files | "parent_observation_id of #15?" |

### When to Use Each Mode

| Scenario | Recommended Mode |
|----------|------------------|
| Quick triage / cost analysis | `--fast` |
| "Where does X come from?" (common values) | `--fast` |
| Deep dive into specific observation | Full (no `--fast`) |
| Need complete tool output (>5KB) | Full (no `--fast`) |
| Analyzing many traces | `--fast` (saves disk) |

## Benchmarks

### Test Traces

| Trace ID | Name | Observations | Complexity |
|----------|------|--------------|------------|
| `0dd243840d794a46` | AskFast | 16 | Simple |
| `b2b77d333d67562b` | V2 | 46 | Complex |

### Speed Comparison

| Trace | Observations | Full Mode | Fast Mode | Speedup |
|-------|--------------|-----------|-----------|---------|
| Trace 1 (AskFast) | 16 | 9.05s | 4.59s | **2.0x** |
| Trace 2 (V2) | 46 | 9.62s | 7.61s | **1.3x** |

### Disk Usage Comparison

| Trace | Observations | Full Mode | Fast Mode | Reduction |
|-------|--------------|-----------|-----------|-----------|
| Trace 1 (AskFast) | 16 | 1.3MB | 136KB | **10x smaller** |
| Trace 2 (V2) | 46 | 6.9MB | 388KB | **18x smaller** |

### Time Breakdown

| Component | Time | Notes |
|-----------|------|-------|
| API fetch (fixed) | ~4s | Langfuse API latency, cannot optimize |
| File writing (scales) | 0.5-5s | Depends on observation count |
| uv startup (fixed) | ~0.5s | Python environment init |

### Test Coverage with `--fast` Mode

Tested 20 questions across both traces:

| Result | Count | Percentage |
|--------|-------|------------|
| **PASS** | 17 | 85% |
| **PARTIAL** | 3 | 15% |
| **FAIL** | 0 | 0% |

**PARTIAL cases**: Data origin questions may show values in LLM observations (which received data from tools) rather than the original TOOL observation, because:
- Tool outputs can exceed 5KB truncation limit
- Values get indexed from wherever they first appear in visible content
- LLM outputs include tool results, so values appear there too

### Test Results Detail

#### Trace 1 Tests (16 observations)

| Test | Question | --fast Result |
|------|----------|---------------|
| 1 | Basic Analysis | PASS |
| 2 | Data Origin ($33.3M) | PARTIAL - shows LLM not tool |
| 3 | Data Origin (83.5%) | PARTIAL - shows LLM not tool |
| 4 | Data Origin (address) | PASS |
| 5 | Execution Flow | PASS |
| 6 | LLM Decisions | PASS |
| 7 | Cost Analysis | PASS |
| 8 | Tool Calls | PASS |
| 9 | Bottleneck Analysis | PASS |
| 10 | Error Detection | PASS |

#### Trace 2 Tests (46 observations)

| Test | Question | --fast Result |
|------|----------|---------------|
| 11 | Multi-Model Cost | PASS |
| 12 | Team Planner Count | PASS |
| 13 | Tool Usage Summary | PASS |
| 14 | Data Origin ($200) | PASS |
| 15 | Find URL Source | PASS |
| 16 | Execution Bottleneck | PASS |
| 17 | Twitter Data Found | PASS |
| 18 | Internal Data Source | PARTIAL - truncated output |
| 19 | Follow-up Questions | PASS |
| 20 | Compare Models Used | PASS |

### Summary

| Metric | Full Mode | Fast Mode |
|--------|-----------|-----------|
| Speed | Baseline | **1.3-2x faster** |
| Disk | Baseline | **10-18x smaller** |
| Test coverage | 100% | 85% |
| Best for | Deep analysis | Quick triage |

## How Data Is Fetched

`fetch_trace.py` uses the Langfuse SDK:

1. **Fetch trace metadata**: `langfuse.api.trace.get(trace_id)`
2. **Fetch all observations**: `langfuse.api.observations.get_many(trace_id=...)` with pagination (up to 500)
3. **Process and save**: Structured files in `/tmp/trace_analysis/<id>/`

SDK: Uses the `langfuse` Python package directly (auto-installed via PEP 723 inline metadata).
Config: `~/.config/langfuse/config.json` (see `references/setup.md`).

## How Key Values Are Indexed

`fetch_trace.py` extracts searchable values using regex patterns:

```python
patterns = {
    "numbers": r'\$[\d,]+\.?\d*[MBKmk]?|...',  # $33.3M, 1,234.56, 83.5%
    "addresses": r'0x[a-fA-F0-9]{8,64}',        # Ethereum addresses
    "urls": r'https?://[^\s\"\'\]>]+'           # URLs
}
```

Creates `key_values.txt` with format: `VALUE | #OBS_NUM | OBS_NAME | INPUT/OUTPUT`

## Observation Types

| Type | Meaning | Data Origin |
|------|---------|-------------|
| `TOOL` | External API/data fetch | Tool fetched from external source |
| `GENERATION` | LLM output | LLM calculated or generated it |
| `SPAN` | Internal processing | Passed through from parent |

## Data Origin Tracing Logic

To determine where a value originated:

1. Find observation with value in OUTPUT
2. Check if same observation has value in INPUT
   - **Not in input** → This observation **generated** the value
   - **In input** → Value came from parent, trace upward via `call_tree.txt`

## Design Decisions

1. **Pre-indexed values** (`key_values.txt`) - Fast lookup without grepping large files
2. **Separate I/O files** - Each observation has `_input.txt` and `_output.txt` for targeted reading
3. **Truncated summaries** - `tools_only.txt`/`llm_only.txt` show 500-800 chars, enough to identify
4. **Call tree visualization** - Parent-child relationships and timing at a glance
5. **Cache by default** - Skip re-fetch if trace already exists
6. **--fast mode** - Trade completeness for speed/disk when full content not needed

## File Generation

| File | Generator Function | Purpose |
|------|-------------------|---------|
| `call_tree.txt` | `build_call_tree()` | Hierarchical view with timing |
| `tools_only.txt` | `build_tools_summary()` | Tool calls with truncated I/O |
| `llm_only.txt` | `build_llm_summary()` | LLM generations with outputs |
| `cost_summary.txt` | `build_cost_summary()` | Token usage by model |
| `key_values.txt` | `extract_key_values()` | Indexed numbers/addresses |

## Session Analysis

Sessions group multiple traces from a single conversation. Use `--session` to fetch all traces at once.

### Session Output Structure

```
/tmp/trace_analysis/sessions/<session_id>/
├── session_meta.json        # Session metadata
├── session_timeline.txt     # Chronological list of traces with user inputs
├── session_cost_summary.txt # Aggregated costs across all traces
└── traces/
    ├── 01_<trace_id>/       # First trace (numbered by conversation order)
    │   ├── trace_input.txt
    │   ├── trace_output.txt
    │   ├── key_values.txt
    │   ├── call_tree.txt
    │   └── ...
    └── 02_<trace_id>/       # Second trace
        └── ...
```

### Session Files

| File | Purpose |
|------|---------|
| `session_meta.json` | JSON with trace IDs, timestamps, user inputs |
| `session_timeline.txt` | Human-readable chronological trace list |
| `session_cost_summary.txt` | Aggregated token usage and costs by model |

### Cross-Trace Analysis

For questions like "where does the BTC price come from?" when it's not in the current trace:

1. **Check session_timeline.txt** to understand conversation flow
2. **Grep across all traces** for the value:
   ```bash
   grep -r "97234" /tmp/trace_analysis/sessions/<id>/traces/*/key_values.txt
   ```
3. **Trace backwards**: If value appears in trace N's INPUT but not OUTPUT, check trace N-1

### Use Cases for Session Analysis

| Scenario | Approach |
|----------|----------|
| "What was the total cost of this conversation?" | Read `session_cost_summary.txt` |
| "Where did the data in the 3rd response come from?" | Check `traces/03_*/key_values.txt`, trace back if needed |
| "Show me the conversation flow" | Read `session_timeline.txt` |
| "Which model was used most?" | Read `session_cost_summary.txt` BY MODEL section |

### Session Performance

| Traces | --fast Mode | Full Mode |
|--------|-------------|-----------|
| 3 traces | ~15s, ~1.2MB | ~30s, ~20MB |
| 10 traces | ~50s, ~4MB | ~100s, ~70MB |

**Recommendation**: Always use `--fast` for sessions unless you need full observation content.

## Storage Estimates

| Mode | Trace Complexity | Observations | Approx Size |
|------|------------------|--------------|-------------|
| Full | Simple (AskFast) | ~16 | ~1.3MB |
| Full | Complex (V2) | ~46 | ~7-9MB |
| Full | Very Complex | ~100+ | ~15MB+ |
| --fast | Any | Any | ~400KB |

After 100 traces (full mode): **200-700MB**
After 100 traces (--fast mode): **~40MB**
After 10 sessions (avg 5 traces, --fast): **~20MB**
