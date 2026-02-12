---
name: surf-data-langfuse-trace
description: Start the Langfuse trace analysis interactive CLI. Use when analyzing traces, debugging agent execution, investigating performance issues, or examining Langfuse observations.
---

# Trace Analysis Skill

Fetch Langfuse trace data to local files and analyze using file search tools.

Supports two modes:
- **Single trace**: Analyze one trace by ID
- **Session**: Analyze all traces in a conversation session

---

## Single Trace Analysis

### Step 1: Fetch Trace Data

When user provides a trace ID, run `fetch_trace.py` from this skill's directory:

```bash
# Standard fetch (uses cache if exists)
uv run SCRIPT_PATH <TRACE_ID>

# Fast mode (2x faster, 24x smaller - skips individual observation files)
uv run SCRIPT_PATH <TRACE_ID> --fast

# Force re-fetch (ignore cache)
uv run SCRIPT_PATH <TRACE_ID> --force
```

> **SCRIPT_PATH**: Resolve the absolute path to `fetch_trace.py` in this skill's directory before running.

**Performance:**
| Mode | Time | Disk |
|------|------|------|
| Cached | instant | - |
| --fast | ~5s | ~400KB |
| Full | ~10s | ~9MB |

Files are saved to `/tmp/trace_analysis/<trace_id_prefix>/`

### Step 2: Choose the Right File

| Question Type | Read This File |
|--------------|----------------|
| "Where does $X come from?" | `key_values.txt` first, then observation file |
| "Show execution flow" | `call_tree.txt` |
| "What tools were called?" | `tools_only.txt` |
| "What did the LLM decide?" | `llm_only.txt` |
| "How much did this cost?" | `cost_summary.txt` |
| "Show observation N" | `observations/00N_*.txt` |
| "Find text X" | Grep `all_outputs.txt` |

### Step 3: Answer Questions

#### For "Where does X come from?"

1. Grep `key_values.txt` for the value
2. Note the observation number and type (e.g., `#004 | external_search | OUTPUT`)
3. Read `observations/004_*_output.txt` for full context
4. Report: source tool, observation ID, and what data source it came from

#### For execution/cost/tool questions

Read the appropriate summary file directly and report findings.

### File Reference

```
/tmp/trace_analysis/<id>/
├── call_tree.txt            # Hierarchical execution with timing
├── cost_summary.txt         # Token usage and costs by model
├── tools_only.txt           # Tool calls with inputs/outputs
├── llm_only.txt             # LLM generations with outputs
├── key_values.txt           # Indexed numbers/addresses for lookup
├── all_outputs.txt          # Full text for grep searches
├── trace_meta.json          # Trace metadata
├── trace_input.txt          # User's original input
├── trace_output.txt         # Final output
└── observations/
    ├── 001_<name>.json      # Full observation data
    ├── 001_<name>_input.txt # Observation input
    └── 001_<name>_output.txt# Observation output
```

### Observation Types

- **TOOL** = External data fetch (this is usually the data source)
- **GENERATION** = LLM output (LLM generated/calculated the value)
- **SPAN** = Internal processing (value passed through)

---

## Session Analysis

When user provides a session ID (or asks about a conversation/session):

### Step 1: Fetch Session Data

```bash
# Fetch all traces in a session
uv run SCRIPT_PATH --session <SESSION_ID>

# Fast mode (recommended for sessions with many traces)
uv run SCRIPT_PATH --session <SESSION_ID> --fast
```

Files are saved to `/tmp/trace_analysis/sessions/<session_id_prefix>/`

### Step 2: Understand the Session

| Question Type | Read This File |
|--------------|----------------|
| "What happened in this session?" | `session_timeline.txt` |
| "Total cost of session?" | `session_cost_summary.txt` |
| "What was the Nth query?" | `session_timeline.txt` then `traces/0N_*/trace_input.txt` |
| "Where did value X come from?" | Grep across `traces/*/key_values.txt` |

### Step 3: Cross-Trace Analysis

For questions like "where does the BTC price in trace 3 come from?":

1. Check if value appears in earlier traces:
   ```bash
   grep -r "97234" /tmp/trace_analysis/sessions/<id>/traces/*/key_values.txt
   ```

2. If found in trace N's INPUT but not OUTPUT, trace back to trace N-1

3. Find the original TOOL observation that fetched the data

### Session File Reference

```
/tmp/trace_analysis/sessions/<session_id>/
├── session_meta.json        # Session metadata (trace list, user queries)
├── session_timeline.txt     # Chronological trace list with inputs
├── session_cost_summary.txt # Aggregated costs across all traces
└── traces/
    ├── 01_<trace_id>/       # First trace (numbered by order)
    │   ├── trace_input.txt
    │   ├── trace_output.txt
    │   ├── key_values.txt
    │   └── ...
    └── 02_<trace_id>/       # Second trace
        └── ...
```

---

## Cache Management

```bash
# List cached traces with sizes
uv run SCRIPT_PATH --list

# Clean traces older than 7 days
uv run SCRIPT_PATH --clean

# Delete all cached traces
uv run SCRIPT_PATH --clean-all
```
