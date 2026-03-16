# Vibe System Architecture

Read this to understand how the vibe coding system works end-to-end. Essential context for analyzing session issues.

## Overview

```
Frontend → muninn-api → urania-agent → sandbox (bwrap) → Claude SDK
              ↕ Redis         ↕ Redis        ↕ stdin/stdout
           (SSE events)   (pod affinity)   (JSON Lines IPC)
```

## 1. Sandbox Lifecycle

**Key files**: `urania/src/agent_mode/session_manager.py`, `executor.py`

Each vibe session gets a **long-lived bubblewrap process** that persists across chat turns.

### Spawn

```
session_manager.get_or_create(session_id, user_id, sdk_session_id)
  → executor.spawn_vibe_process()
    → starts bwrap with:
      - /workspaces/{user_id} mounted (EFS)
      - HTTP_PROXY on port 9999 (API key injection)
      - ANTHROPIC_BASE_URL on port 9998 (LLM routing)
      - runs sandbox_runner.py inside sandbox
  → waits for {"type": "session_ready"} event on stdout
  → registers pod affinity in Redis: vibe:pod:session:{session_id} → pod_ip
```

### Communication (stdin/stdout JSON Lines)

Commands (api.py → sandbox_runner.py):
- `{"cmd": "message", "message": "...", "sdk_session_id": "..."}` — send user message
- `{"cmd": "build", "timeout": 600}` — build project
- `{"cmd": "cancel"}` — cancel current turn
- `{"cmd": "shutdown"}` — graceful shutdown

Events (sandbox_runner.py → api.py):
- `session_ready` — sandbox initialized
- `thinking` / `message` / `tool` / `tool_result` — agent loop events
- `artifact_created` / `file_content` — file write notifications
- `turn_done` / `done` — turn/session completion
- `error` — failure

### Idle Cleanup

Every 5 minutes, SessionManager checks idle processes:
- Default idle timeout: **30 minutes** (`DEFAULT_SESSION_IDLE_TIMEOUT=1800s`)
- Sends `{"cmd": "shutdown"}` then kills if unresponsive
- Removes Redis keys, unregisters preview port

### Recovery (get_or_create)

When user returns to a dead sandbox:

```
1. Check if session.is_alive and session.ready
   → Alive: reuse (apply grace period: 45s for new, 180s for recovery)

2. L2 health check: is backend port listening?
   → Not listening: attempt _recover_backend (send "touch" command)

3. L3 respawn: full restart
   → Fetch user secrets from Bifrost
   → spawn_vibe_process() again
   → Wait for session_ready
```

**Grace periods**: New sessions get 45s (dev servers warming up), recovery-spawned get 180s (npm install takes 75-150s).

## 2. Claude SDK Usage

**Key file**: `urania/src/agent_mode/sandbox_runner.py`

The SDK runs **inside the sandbox** — urania doesn't call Claude API directly.

### SDK Session Management

```
New session (sdk_session_id=None):
  → SDK creates fresh conversation
  → New output dir: outputs/{YYYYMMDD_HHMMSS}/

Resume session (sdk_session_id set):
  → SDK restores conversation history from its own state
  → Reuses existing output dir
```

The `sdk_session_id` is Claude SDK's internal ID (different from vibe session_id). It's stored in `SessionInfo` and passed to sandbox on each message.

### Tool Calls

SDK tool events flow through the JSON Lines IPC:
- `{"type": "tool", "name": "Write", "input": {...}, "tool_use_id": "toolu_xxx"}` — tool invocation
- `{"type": "tool_result", "output": "...", "tool_use_id": "toolu_xxx"}` — result matching

File writes are tracked by `tool_use_id` in `pending_writes`/`pending_edits` dicts for artifact detection.

### Message Counting

In Datadog, `[SandboxRunner] Message #N` shows the raw SDK message stream:
- `AssistantMessage` — Claude's response (text, tool calls)
- `UserMessage` — tool results fed back to Claude
- Rapid `UserMessage` bursts (10+ in <1s) = parallel tool results

A single user "turn" typically produces 5-50+ messages depending on how many tools the agent uses.

## 3. Muninn ↔ Urania SSE

**Key files**: `muninn/internal/service/crypto_agent_chat.go`, `urania/src/agent_mode/api.py`

### Request Flow

```
1. Frontend → muninn: POST /v1/crypto-agent/sessions/{id}/chat
2. Muninn acquires Redis session lock (TTL: 1 hour)
3. Muninn calls urania /agent/chat/stream (internal HTTP)
4. Urania's event_generator yields SSE events from sandbox
5. Muninn stores each event in Redis (RPUSH, TTL: 4 hours, max 10000)
6. Muninn streams events back to frontend as SSE
```

### Reconnection (Last-Event-ID)

```
1. Frontend reconnects with Last-Event-ID header
2. Muninn replays events after that ID from Redis
3. Checks session status in Redis:
   - "running" → continue streaming from Redis
   - "done"/"error"/"cancelled" → return final events
```

Event IDs are zero-padded (`00001#000001`) for string comparison ordering.

### Session Lock

- Key: session UUID, TTL: 1 hour
- Prevents concurrent messages to same session
- If lock fails: check if session running (reconnect) or truly locked (409 Conflict)

**Gotcha**: Lock TTL (1h) < Event TTL (4h) — lock can expire during long-running agent turns.

## 4. Proxy & LLM Routing

**Key file**: `urania/src/agent_mode/proxy.py`

### Dual-Port Architecture

```
Port 9998: LLM requests (Claude API)
  - Claude SDK sends here (via ANTHROPIC_BASE_URL)
  - Routes to CommonStack first, fallback to direct Anthropic
  - Injects API key (sandbox never sees it)

Port 9999: Data/tool requests
  - HTTP_PROXY for tools (curl, etc.)
  - /proxy/{category}/{endpoint} → Hermod data API
  - Injects Hermod Bearer token
```

### API Key Injection

Sandbox environment has `ANTHROPIC_API_KEY = "placeholder"`. The proxy intercepts requests and injects real keys based on destination:
- `api.commonstack.ai` → X-Api-Key header
- `api.anthropic.com` → X-Api-Key header (direct fallback)
- `api.x.ai` → Authorization Bearer

### Token Usage & Credit Tracking

```
1. Proxy parses streaming response from Claude API
2. Extracts token counts from final message_delta
3. Pushes TokenUsage to event_generator via async queue
4. Event generator:
   - Emits "token_usage" SSE event to frontend
   - Logs to Langfuse tracer
   - Deducts credits via Hermod API
5. Budget thresholds: WARN (50%), STOP (80%), HARD_STOP (100%)
```

### CommonStack Fallback

When CommonStack returns 404 ("model not found"):
- Proxy logs warning and retries with direct Anthropic API
- Adds ~1-2s latency per call
- Common for Haiku model (not registered in CommonStack)
- Does NOT break the agent loop — just slower

## 5. State Preservation Summary

| State | Storage | TTL | What's in it |
|-------|---------|-----|-------------|
| Pod affinity | Redis `vibe:pod:session:{sid}` | 30 min (refreshed) | Which pod owns session |
| Provider | Redis `vibe:provider:session:{sid}` | Session lifetime | "anthropic" or "xai" |
| Project dir | Redis `vibe:project_dir:session:{sid}` | Session lifetime | EFS path to output dir |
| SSE events | Redis `crypto:session:{sid}:events` | 4 hours | All SSE events for replay |
| Session status | Redis `crypto:session:{sid}:status` | 4 hours | running/done/cancelled/error |
| Session lock | Redis (muninn) | 1 hour | Prevents concurrent messages |
| Code output | EFS `/workspaces/{uid}/workspace/outputs/` | Until cleanup | Generated project files |
| SDK state | EFS `/workspaces/{uid}/.claude/` | Until cleanup | Claude SDK conversation history |
| Session record | Muninn DB `crypto_agent_sessions` | Permanent | user_id, mode, timestamps |
