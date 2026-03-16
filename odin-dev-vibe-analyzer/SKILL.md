---
name: odin-dev-vibe-analyzer
description: Comprehensive vibe coding session analysis combining Langfuse (agent reasoning), Datadog (service telemetry), and EFS (code output). Use when user asks to analyze a vibe session, debug vibe coding issues, review agent performance, inspect sandbox output, or says /odin-dev-vibe-analyzer. Accepts session_id, user_id, or user email as input.
---

# Vibe Coding Session Analyzer

Deep analysis of vibe coding sessions from three dimensions:

| Dimension | Source | What it reveals |
|-----------|--------|-----------------|
| **Agent Reasoning** | Langfuse | Chat history, ReAct loop, tool calls, LLM thinking, token costs |
| **Service Telemetry** | Datadog | Cross-pod communication, session lifecycle, errors, latency |
| **Code Output** | EFS | Generated project files, code quality, structure |

## Input Resolution

The skill accepts three input types. Resolve them to `session_id` + `user_id` before collecting data.

### 1. Session ID (direct)

```bash
SESSION_ID="5b1e6162-2a04-457c-9624-8eea9d996411"
# → Use tiered resolution (Redis → DB → Datadog) via efs-pull.sh to get user_id
bash surf-skills/odin-dev-sandbox/scripts/efs-pull.sh --session "$SESSION_ID" tree
```

### 2. User ID (list sessions, pick latest)

```bash
USER_ID="2430ede5-3fab-4e91-9fb5-243d4ee951e0"
# → Query Datadog for recent sessions by this user
cd surf-skills/odin-dev-datadog
uv run python scripts/ddlog.py query "@user_id:$USER_ID AND SessionManager AND \"New session\"" --time 7d -n 20
# → Pick the session_id from results
```

### 3. User Email (resolve to user_id first)

```bash
EMAIL="user@example.com"
# → Query muninn DB via odin-data-db skill
# SQL: SELECT id FROM users WHERE email = '$EMAIL' OR google_email = '$EMAIL' LIMIT 1
# → Then follow User ID flow above
```

## Data Collection

After resolving to `session_id`, collect data from all three sources. Run these in parallel where possible.

### A. Langfuse — Agent Reasoning

The Langfuse session_id used by urania is **not** the same as the vibe session_id. The vibe session_id is stored as a trace attribute. Find traces by querying Datadog for the Langfuse trace_id:

```bash
# Step 1: Find Langfuse trace_id from Datadog logs
cd surf-skills/odin-dev-datadog
uv run python scripts/ddlog.py query "@session_id:$SESSION_ID AND LangfuseTracer" --time 7d -n 5 --verbose

# Step 2: If trace_id found, fetch from Langfuse
cd surf-skills/odin-data-langfuse-trace
uv run fetch_trace.py <trace_id> --fast

# Key files to read:
#   call_tree.txt     — execution flow and timing
#   tools_only.txt    — what tools/APIs the agent called
#   llm_only.txt      — LLM decisions and reasoning
#   cost_summary.txt  — token usage and costs
```

### B. Datadog — Service Telemetry

```bash
cd surf-skills/odin-dev-datadog

# Full session timeline
uv run python scripts/ddlog.py session $SESSION_ID --time 7d --sort asc -n 500

# Errors and warnings only
uv run python scripts/ddlog.py session $SESSION_ID --time 7d --level warn -n 100 --verbose

# Performance metrics (startup, LLM latency, proxy)
uv run python scripts/ddlog.py query "@session_id:$SESSION_ID AND STARTUP_PERF" --time 7d
uv run python scripts/ddlog.py query "@session_id:$SESSION_ID AND LLM" --time 7d
uv run python scripts/ddlog.py query "@session_id:$SESSION_ID AND DATA_API_PERF" --time 7d
```

### C. EFS — Code Output

```bash
# File tree
bash surf-skills/odin-dev-sandbox/scripts/efs-pull.sh --session $SESSION_ID tree

# Pull to local for analysis
bash surf-skills/odin-dev-sandbox/scripts/efs-pull.sh --session $SESSION_ID pull

# Files are at /tmp/efs-pull/<user_id>/workspace/outputs/<project>/
```

## Analysis Framework

**Read `references/analysis-methodology.md` before analyzing.** Follow the 6 phases in order:

1. **User Intent** — what did the user actually ask? (read their message, not the agent's plan)
2. **Agent Execution** — what did the agent do? (message flow, tool calls, turn count)
3. **Conversation Flow** — how did multi-turn interaction play out? (reconnects, user follow-ups)
4. **Code Output** — does the output match intent? (plan vs actual, read core files)
5. **Infrastructure** — did infra issues affect the outcome? (only report if causally linked)
6. **Root Cause** — why is the result what it is? (verdict + evidence chain)

**Reference docs** (read when relevant, not upfront):
- `references/analysis-methodology.md` — full 6-phase checklist and report template
- `references/vibe-system-architecture.md` — sandbox lifecycle, SDK usage, SSE flow, proxy routing, state model
- `references/sse-architecture.md` — SSE 3-layer model, "agent stopped" diagnostics
- `references/scaffold-and-build.md` — why reading scaffold files is expected; build only triggers on deploy, not between turns
- `references/setup.md` — credential setup guide (Datadog/Langfuse/kubectl); read when data collection commands fail with auth errors

## Output Format

Structure the report as:

```markdown
# Vibe Session Analysis: <session_id_short>

## Summary
- User: <email/name> (<user_id_short>)
- Time: <start> → <end> (<duration>)
- Model: <model>
- Status: <outcome>

## Agent Reasoning (Langfuse)
<findings>

## Service Health (Datadog)
<findings with key metrics table>

## Code Output (EFS)
<file structure + quality notes>

## Issues Found
1. <issue with evidence from specific dimension>

## Recommendations
1. <actionable suggestion>
```
