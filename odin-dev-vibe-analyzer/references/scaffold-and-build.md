# Scaffold Mechanism & Build Timing

When analyzing vibe sessions, understand the design intent behind scaffold file reads and build triggers to avoid misdiagnosis.

## Scaffold: GenAPI-Generated API Client Code

### Generation Flow

1. `scaffold_vite.py` creates frontend + backend skeleton (frontend/ + backend/)
2. `gen_api.py` generates **typed API clients** from hermod's OpenAPI spec (`/gateway/openapi.json`)
3. Output written to `lib/` directories in both frontend and backend:
   - `types-{category}.ts` — TypeScript type definitions per domain
   - `api-{category}.ts` — fetch functions + React Query hooks per domain
   - `api.ts` — core HTTP client (baseURL, error handling, auth)
   - `API_INDEX.md` — index of all API endpoints

### Covered Domains (11)

Market, Project, Social, Wallet, Token, News, Onchain, Web, Fund, Search, Prediction Market

### Cache Mechanism

- GenAPI uses a local file cache (`GEN_API_CACHE_DIR`), default TTL 600s, max age `_DEFAULT_MAX_AGE_SEC`
- Cache validated by swagger spec hash + code version hash
- Background async refresh: does not block session startup
- Log markers: `Cache HIT — copied N files` or `Cache MISS — generating`

### Reading Scaffold Files Is Expected Behavior

**Do NOT flag agent Read calls on scaffold files as "redundant" or "wasteful".**

Scaffold-generated API client code serves as the agent's API documentation. The agent reads these files to understand:
- Which APIs are available (API_INDEX.md)
- Parameter and return types for each API (types-*.ts)
- How to call them (function signatures and React Query hooks in api-*.ts)

This is equivalent to the agent reading API docs and then writing client code, except the scaffold has already completed the "read docs → write client" step. The agent only needs to read the result, understand the interface, and call it in business code.

**Valid optimization to look for:** whether the agent reads scaffold files unrelated to the task (e.g., task only involves market data but agent reads all 11 domains). Selective reading is a reasonable optimization direction.

## Build: Only Triggered on Deploy

### Build Is NOT Incremental Verification Between Agent Turns

Build (`npm run build`) trigger timing:

| Trigger | Command | When |
|---------|---------|------|
| **User clicks Deploy** | `{"cmd": "build", "timeout": 600}` | First step of deploy flow |
| **Never auto-triggered** | — | No build between agent turns |

Code path:
```
User Deploy → api.py._run_deploy_build_and_package_or_raise()
  → session_manager.build_session() → stdin write {"cmd": "build"}
    → sandbox_runner._run_build_command() → npm run build
```

### Feedback Sources During Development

Agent feedback during coding comes **not from build**, but from:

1. **Vite Dev Server (HMR)** — auto hot-reload on file changes; frontend compile errors surfaced via dev_server error events
2. **Bash tool output** — stdout/stderr from `npm install`, `node server.js`, etc.
3. **Preview page loads** — PreviewProxy requests to frontend; 502/ConnectError exposes runtime issues
4. **User feedback** — user sees preview and sends next message

### Build Event Chain

```
build_status(running) → build_log(line) → build_done / build_error(build_failed|build_timeout)
```

On failure, `build_error` includes the last 2000 chars of npm output for diagnostics.

### Analysis Guidelines

- **Do NOT suggest "run build between agent turns for incremental verification"** — this is not the current architecture; the dev server already provides real-time feedback
- **Build failure ≠ agent code is wrong** — could be TypeScript strict mode warnings, missing deps, or build environment issues
- **Distinguish build_error stage** — occurs during deploy phase, not during agent coding phase
