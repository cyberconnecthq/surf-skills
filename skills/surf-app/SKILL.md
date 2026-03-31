---
name: surf-app
description: >-
  Build crypto data web apps with the Surf SDK. Scaffolds a full-stack project
  (Vite + React 19 + Express + Tailwind) with typed data hooks and server-side
  API access. Use when the user wants to build a dashboard, app, tool, or
  visualization that displays crypto data. Triggers on "build a price tracker",
  "create a whale dashboard", "make a DeFi comparison page", etc.
---

# Surf App

Build full-stack crypto data apps with `create-surf-app` and `@surf-ai/sdk`.

- **This skill**: Build a web app / dashboard / visualization with crypto data.
- **The `surf` skill**: Research, investigate, or fetch data via CLI (no web UI).

## Scaffold and Start

Run these commands exactly — do not modify or skip steps:

```bash
# 1. Scaffold (ports auto-configured from environment)
npx create-surf-app .

# 2. Install dependencies
npm install --prefix backend
npm install --prefix frontend

# 3. Read the project rules BEFORE writing any code
cat CLAUDE.md

# 4. Start dev servers (backend first, then frontend)
npm run dev --prefix backend &
npm run dev --prefix frontend

# 5. Verify backend is running (wait a few seconds for startup)
curl -s http://localhost:$VITE_BACKEND_PORT/api/health
# Expected: {"status":"ok"} — if you see this, backend is ready. Do NOT restart it.
```

**IMPORTANT — do NOT:**
- Use `npx vite` or `npx vite --port ...` — always use `npm run dev`
- Pass `--port` flag to dev commands — port is pre-configured in `frontend/.env`
- Restart dev servers after `npm install` — Vite auto-discovers new deps, backend uses `node --watch`
- Try to kill processes or free ports — if `curl localhost:$VITE_BACKEND_PORT/api/health` returns `{"status":"ok"}`, the server is already running

Then **read the generated `CLAUDE.md`** at the project root — it has the full SDK reference, built-in endpoints, and rules for which files not to modify.

After `npm install`, also read SDK and theme docs for detailed patterns:
- `cat frontend/node_modules/@surf-ai/sdk/README.md` — database (Drizzle ORM), cron jobs, web search, data strategy (market vs exchange), backend composition patterns
- `cat frontend/node_modules/@surf-ai/theme/CHARTS.md` — **MUST read before writing any ECharts code** — Surf flat style contract, tooltip formatter, chart colors, time series tabs
- `cat frontend/node_modules/@surf-ai/theme/DESIGN-SYSTEM.md` — Surf semantic tokens (bg/fg/border), tag colors, visualizer palette

## Project Structure

```
frontend/src/App.tsx           ← Main UI, build here
frontend/src/components/       ← Add components
backend/routes/*.js            ← API routes (auto-mounted at /api/{name})
backend/db/schema.js           ← Database tables (Drizzle ORM)
CLAUDE.md                      ← Project rules (READ FIRST)
```

Do not modify: `vite.config.ts`, `server.js`, `entry-client.tsx`, `entry-server.tsx`, `index.html`, `index.css`.

## Workflow: Data Discovery → Code

**Always start by exploring available data with the `surf` CLI**, then map directly to SDK code. The CLI → SDK mapping is mechanical (see Step 2). Do NOT run `node -e` to test individual endpoints.

### Step 1: Discover endpoints with CLI

```bash
surf sync                                    # Download API spec (first time)
surf list-operations -g                      # List all endpoints by category
surf market-price --help                     # See params, enums, response schema
surf market-price --symbol BTC --time-range 7d   # Fetch sample data, verify shape
```

CLI flags use **kebab-case** (e.g. `--time-range`). `surf` is a global command (NOT `npx surf`).

### Step 2: Check SDK exports before writing code

**Do not guess hook or method names.** After `npm install`, read actual exports:

```bash
grep -o 'function use[A-Za-z]*' frontend/node_modules/@surf-ai/sdk/dist/react/index.js | sort
```

**Naming convention — CLI → SDK:**
- CLI: `surf market-ranking --limit 5` → Frontend: `useMarketRanking({ limit: 5 })` or `useInfiniteMarketRanking({ limit: 5 })`
- CLI: `surf market-ranking --limit 5` → Backend: `dataApi.market.ranking({ limit: 5 })`
- CLI flags are **kebab-case** (`--time-range`), SDK params are **snake_case** (`{ time_range: '7d' }`)

**Key rules:**
- Use **exact** hook names from the `grep` output — if only `useInfinite*` exists (no plain `use*`), use the infinite version and access `data.pages[0]` for the first page
- Backend: `const { dataApi } = require('@surf-ai/sdk/server')` — method names match CLI commands (`surf market.price` → `dataApi.market.price()`)
- Escape hatch: `dataApi.get(path, params)` if a typed method doesn't exist

### Step 3: Write code

Write frontend and backend code using the confirmed names from Step 2. Do not run additional `node -e` calls to test individual endpoints — the SDK methods are guaranteed to work if the name exists in the export list.

## Frontend — SDK Hooks

```tsx
import { useMarketPrice } from '@surf-ai/sdk/react'

const { data, isLoading } = useMarketPrice({ symbol: 'BTC', time_range: '1d' })
// data.data → items array; data.meta → pagination/credits
```

The `/proxy/*` route is built-in — hooks automatically call `/proxy/market/price` which the Express backend forwards to the data API. No manual fetch needed.

## Backend — dataApi

```js
// backend/routes/portfolio.js → /api/portfolio
const { dataApi } = require('@surf-ai/sdk/server')
const { Router } = require('express')
const router = Router()

router.get('/', async (req, res) => {
  const data = await dataApi.wallet.detail({ address: req.query.address })
  res.json(data)
})

module.exports = router
```

Escape hatch: `dataApi.get('any/path', params)` / `dataApi.post('any/path', body)`.

Built-in endpoints (do not recreate): `/api/health`, `/api/__sync-schema`, `/api/cron`, `/proxy/*`.

## Styling

Tailwind CSS 4 + `@surf-ai/theme` (dark default). Use `shadcn/ui` components (`npx shadcn@latest add button`), `echarts-for-react` for charts, `lucide-react` for icons. All pre-installed.
