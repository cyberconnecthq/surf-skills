# Vibe Session Analysis Methodology

Read this before starting any session analysis. Follow the phases in order — each phase builds on the previous one's findings.

## Phase 1: User Intent (must do first)

**Question: What did the user actually ask for?**

Sources:
- Datadog: `@session_id:XXX AND "Command: message"` → first message triggers
- Langfuse: `trace_input.txt` → full user prompt
- EFS: `PLAN.md` → agent's interpretation of the request

Checklist:
- [ ] Read the user's original message (not the agent's plan)
- [ ] Is the request clear and scoped, or vague and open-ended?
- [ ] Is the request achievable in a single agent turn?
- [ ] Did the user send follow-up messages? What did they say?

**Why first**: Without knowing what the user wanted, you can't judge if the output is "good" or "bad." A 50-file project might be perfect for "build me a dashboard" but terrible for "fix the button color."

## Phase 2: Agent Execution Flow

**Question: What did the agent actually do, step by step?**

Sources:
- Datadog: `[SandboxRunner] Message #N` — the full message flow
- Datadog: `[LLM Input Capture]` — model calls with message counts
- Langfuse: `call_tree.txt`, `tools_only.txt` — structured execution trace

Checklist:
- [ ] How many turns (Opus calls)? Count `model=anthropic/claude-opus` entries
- [ ] How many tool calls per turn? Look at UserMessage bursts between AssistantMessages
- [ ] What tools were called? (file write, bash, hermod API, etc.)
- [ ] How many sub-task calls (Haiku)? These are skill detection, language detection, etc.
- [ ] Did the agent hit context limits? (message count >80, or sudden stop after long run)
- [ ] Was there a `done event` or did it just stop?

Key patterns:
- `AssistantMessage → multiple UserMessages → AssistantMessage` = one tool-call turn
- Rapid `UserMessage` burst (10+ in <1s) = tool_results from parallel tool calls
- `Message #N` stops incrementing = agent turn ended (check if cleanly or abruptly)

## Phase 3: Conversation Flow (multi-turn sessions)

**Question: How did the user and agent interact over time?**

Sources:
- Datadog: `"New session" OR "Session dead" OR "SSE connection" OR "Query sent"` with `--time 7d`
- Datadog: `"Command: message"` — each user message triggers this

Checklist:
- [ ] How many user messages total across the session lifetime?
- [ ] Time gaps between interactions (user left and came back?)
- [ ] After each reconnect: did the user send a new message or just refresh?
- [ ] Did the user modify their request mid-session? (pivot, scope change)
- [ ] Session dead count — how many times was the sandbox reclaimed?
- [ ] Resume success — after respawn, did the agent recover context correctly?

## Phase 4: Code Output Assessment

**Question: Does the output match what the user asked for?**

Sources:
- EFS: project files pulled to local
- EFS: `PLAN.md` vs actual file list

Checklist:
- [ ] Read PLAN.md — what files did the agent plan to create/modify?
- [ ] Compare plan vs actual: which planned files exist? Which are missing?
- [ ] Read 2-3 core files (not UI components): do they have real logic or are they stubs?
- [ ] Check for common vibe coding issues:
  - Empty/placeholder components (just returns `<div>TODO</div>`)
  - Hardcoded mock data instead of real API integration
  - Import errors (importing modules that don't exist)
  - Missing error handling in API calls
  - `.env` files with placeholder values
- [ ] Does the backend actually call the APIs mentioned in the plan?
- [ ] Does the frontend actually render data from the backend?

## Phase 5: Infrastructure Impact

**Question: Did infrastructure issues affect the outcome?**

Read `references/sse-architecture.md` for SSE layer understanding.

Sources:
- Datadog: errors/warnings, performance metrics

Checklist:
- [ ] CommonStack fallbacks — how many, did they cause visible delays?
- [ ] Hermod API errors — did data fetching fail for any endpoints?
- [ ] Sandbox spawn time — normal (<5s) or slow?
- [ ] Bifrost secrets — available or "encryption not configured"?
- [ ] Did any infrastructure issue directly cause agent to produce incomplete work?

**Important**: Infrastructure issues are only relevant if they caused a user-visible problem. Don't report "50 CommonStack 404s" as a finding unless you can trace it to a specific gap in the output.

## Phase 6: Root Cause & Verdict

**Question: Why is the outcome what it is?**

Synthesize findings from phases 1-5 into one of these verdicts:

| Verdict | Criteria |
|---------|----------|
| **Agent succeeded** | Output matches user intent, code is functional |
| **Agent partially completed** | Some planned features missing — identify which and why |
| **Agent failed** | Output doesn't match intent, or has fundamental issues |
| **User abandoned** | User stopped engaging — check if due to agent quality or external reasons |
| **Infra blocked** | Infrastructure issue directly prevented agent from completing |

For "partially completed" or "failed," identify the root cause:

| Root cause category | How to identify |
|---------------------|-----------------|
| **Plan too ambitious** | PLAN.md scope >> what's achievable in one turn |
| **Context limit hit** | High message count, agent stopped mid-file |
| **API failures** | Hermod/external API errors in logs, missing data in output |
| **User pivot** | User changed requirements mid-session |
| **Sandbox reclaimed** | Session dead during active execution (not idle) |
| **LLM quality** | Code exists but is wrong/shallow (stubs, mock data, broken logic) |

## Report Structure

```markdown
# Session Analysis: <session_id_short>

## What the user wanted
<1-2 sentences from actual user message>

## What happened
<Chronological narrative: agent planned X, executed Y turns, produced Z files>

## Completion assessment
<Planned vs actual file comparison, with specific gaps identified>

## Code quality
<Findings from reading 2-3 core files>

## Root cause of issues
<If applicable, with evidence chain>

## Infrastructure notes
<Only if infra issues affected the outcome>
```
