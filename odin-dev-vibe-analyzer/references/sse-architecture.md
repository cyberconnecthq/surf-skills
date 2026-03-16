# SSE Architecture & Session Lifecycle

Read this when analyzing SSE disconnect patterns or "agent stopped mid-way" reports.

## Three Layers of Connection

```
Browser ←—SSE—→ muninn-api ←—SSE (internal)—→ urania-agent ←—stdin/stdout—→ sandbox (Claude SDK)
  Layer 1: frontend SSE              Layer 2: internal SSE              Layer 3: agent loop
  (can break: network, browser       (stable: K8s internal,             (runs independently,
   sleep, user closes tab)            only breaks if pod dies)           even if Layer 1 drops)
```

## Key Rules

1. **`SSE connection added/removed` in muninn-api = Layer 1 (frontend).** Does NOT affect the agent. Users closing a tab or flaky Wi-Fi shows as SSE disconnect in muninn, but the agent keeps running in urania.

2. **Agent execution continues regardless of Layer 1.** Look at `[SandboxRunner] Message #N` in urania-agent logs — if message numbers keep incrementing, the agent is working fine.

3. **"Session dead, respawning"** = sandbox process was reclaimed (idle timeout or pod reschedule). This IS a real interruption — agent must resume from checkpoint.

4. **"User stopped chatting" ≠ "Agent broke."** Common pattern: user sees SSE drop (Layer 1), thinks agent died, leaves. Agent may have completed the turn successfully. Check the last `Message #N`.

5. **CommonStack 404 → fallback** adds latency per Haiku call (~1-2s each) but does NOT break the agent loop.

## Diagnostic Table

| Symptom | Check | Root cause |
|---------|-------|------------|
| Agent output stopped showing | muninn SSE disconnect? | Layer 1 drop — agent may still be running |
| Agent actually stopped executing | Last `Message #N` number? | Context limit hit, or SDK turn completed normally |
| Session dead on return | Time gap between SSE events? | Sandbox reclaimed after idle timeout |
| Partial code output | Message count vs plan complexity? | Plan too ambitious for single turn |
| High message count (>80) + incomplete | Token usage? | Agent hitting context limits |
