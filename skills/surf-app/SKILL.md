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

## Scaffold

```bash
npx create-surf-app .
```

Ports are read from `VITE_PORT` / `VITE_BACKEND_PORT` env vars (defaults: 5173 / 3001). Override with `--port` and `--backend-port` if needed.

After scaffolding, install dependencies and start dev servers:

```bash
cd backend && npm install && npm run dev &
cd ../frontend && npm install && npm run dev
```

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

**Always start by exploring available data with the `surf` CLI**, then map directly to SDK code. Do NOT run `node -e` to test dataApi — the mapping is mechanical.

### Step 1: Discover endpoints with CLI

```bash
surf sync                                    # Download API spec (first time)
surf list-operations -g                      # List all endpoints by category
surf market-price --help                     # See params, enums, response schema
surf market-price --symbol BTC --time-range 7d   # Fetch sample data, verify shape
```

CLI flags use **kebab-case** (e.g. `--time-range`). `surf` is a global command (NOT `npx surf`).

### Step 2: Check SDK exports before writing code

**Do not guess hook or method names.** The SDK naming doesn't always follow a simple rule from CLI commands. After `npm install`, read the actual exports:

**Frontend hooks:**
```bash
grep -o 'function use[A-Za-z]*' frontend/node_modules/@surf-ai/sdk/dist/react/index.js | sort
```

**Backend dataApi methods:**
```bash
node -e "const { dataApi } = require('@surf-ai/sdk/server'); for (const [domain, methods] of Object.entries(dataApi)) { if (typeof methods === 'object' && methods !== null) { for (const m of Object.keys(methods)) { console.log('dataApi.' + domain + '.' + m + '()') } } }"
```

Run this from the `backend/` directory after `npm install`.

**Key rules:**
- Use **exact** names from the output above — do not derive from CLI command names
- Frontend: some endpoints only have `useInfinite*` hooks (paginated), not plain `use*`. Use the infinite version — access `data.pages[0]` for the first page
- Backend: params use **snake_case** (`{ time_range: '7d' }`) matching CLI flags converted from kebab-case
- Both: there is always a `dataApi.get(path, params)` escape hatch if a typed method doesn't exist

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
