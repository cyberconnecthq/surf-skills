---
name: surf-dev-repo-map
description: >
  Surf platform repository map — maps Norse-named repos to their purposes, tech stacks,
  and inter-service dependencies. Use when navigating the codebase, finding where to fix bugs,
  understanding service ownership, or onboarding to the Surf platform.
  Covers ~41 active repos across app clients, backend services, AI/search, data pipelines, and infra.
---

# Surf Repo Map

Quick reference for finding the right repo when working on the Surf platform. All repos live under `cyberconnecthq/` on GitHub.

## Service Map

```
                    ┌─────────────────────────────────────┐
                    │           Client Layer              │
                    │  surf-website · surf-ios · android  │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │         API Gateways                │
                    │  muninn (main) · hermod · huginn    │
                    │  surf-api-gateway                   │
                    └──┬───────────┬──────────────┬───────┘
                       │           │              │
              ┌────────▼───┐ ┌────▼─────┐ ┌──────▼──────┐
              │  AI/Search │ │ Twitter  │ │  Deploy     │
              │  odin      │ │ argus    │ │  bifrost    │
              │  odin-flow │ │ heimdall │ │             │
              │  urania    │ │          │ │             │
              └────────────┘ └──────────┘ └─────────────┘
                       │           │
              ┌────────▼───────────▼──────────────────────┐
              │            Data Layer                      │
              │  swell (ETH) · helios (SOL) · diver       │
              │  ClickHouse · PostgreSQL · Redis           │
              └───────────────────────────────────────────┘
```

## Quick Lookup

### App / Clients

| Repo | Lang | Purpose |
|------|------|---------|
| `surf-website` | TS | Main Surf web app |
| `surf-ios` | Swift | iOS app |
| `surf-android` | Kotlin | Android app |
| `surf-doc` | MDX | Public documentation site |
| `surf-v2` | Python | Crypto AI agent (Claude Agent SDK, FastAPI + SSE) |
| `remove-vibe` | TS | Surf UI design system and dashboard prototypes |

### Backend Services

| Repo | Lang | Purpose |
|------|------|---------|
| `muninn` | Go | **Main API** — auth, chat/AI streaming, projects, tokens, news, subscriptions, watchlists |
| `hermod` | Go | **New API gateway** — scaffolded from muninn, REST at `/gateway`, being built out |
| `huginn` | Go | **Enterprise API gateway** — B2B multi-tenant AI chat completions, market intelligence |
| `argus` | Go | **Twitter/X analytics** — real-time tweet ingestion (Kinesis), mindshare, sentiment (XAI/Grok) |
| `bifrost` | Go | **Deploy orchestrator** — deploys S3 artifacts to EKS pods for Surf/Urania sandboxes |
| `pluto` | Go | **RPC proxy** — weighted load balancer across EVM RPC providers with failover |
| `surf-api-gateway` | Go | API gateway (routing layer) |
| `surf-chainreader` | TS | On-chain data reader |
| `proto` | Go | **Shared protobuf** — gRPC definitions for all Go services (library, not a running service) |

### AI / Search

| Repo | Lang | Purpose |
|------|------|---------|
| `odin` | Python | Core search/knowledge engine |
| `odin-flow` | Python | AI workflow orchestration (called by muninn via gRPC) |
| `urania` | Python | Coding agent with data_frame compute |
| `recon` | Go+Py | Onchain intelligence — Arkham API proxy, address clustering, CEX deposit attribution |
| `llm-judge-eval-script-version` | Python | LLM-as-judge evaluation scripts |
| `llm-as-judge-check` | Python | LLM judge accuracy checks (precision/recall/F1) |

### Data / Pipeline

| Repo | Lang | Purpose |
|------|------|---------|
| `swell` | Python | **ETH data pipeline** — BigQuery → ClickHouse → dbt (75+ protocols, 6B+ events) |
| `helios` | Python | **SOL data pipeline** — Solana blockchain indexing into ClickHouse (replicating Dune) |
| `diver` | TS | Data analysis tools for Surf |
| `heimdall` | Python | **Twitter/X crawler** — multi-account pool, SQS task queue, Kinesis output to argus |
| `data-check-skill` | Python | Data validation skill for surf db |
| `data-check-script` | Python | Data validation agent scripts |
| `databricks-cyber` | Python | Databricks integration |
| `dune-internal-viewer` | JS | Internal Dune dashboard viewer |
| `token-monitoring` | TS | Token price/volume monitoring |

### Infra / DevOps

| Repo | Lang | Purpose |
|------|------|---------|
| `gitops` | Shell | Production GitOps deployment (ArgoCD) |
| `gitops-stg` | Mustache | Staging GitOps deployment |
| `dagster-staging` | Shell | Dagster orchestration (staging) |
| `OTS` | — | GitOps for deploying external dependencies |
| `surf-skills` | Python | This repo — Claude Code skills |

### Other

| Repo | Lang | Purpose |
|------|------|---------|
| `enterprise-dashboard` | TS | Enterprise customer dashboard |
| `stablecoin-fiat` | TS | Stablecoin/fiat trading dashboard — bid-ask spread monitoring across 10 exchanges |

## Where to Look (Bug Guide)

| Bug Category | Start Here | Then Check |
|---|---|---|
| Auth / login issues | `muninn` (internal/service/auth) | `surf-website`, mobile apps |
| Chat / AI responses | `muninn` (internal/service/chat) | `odin-flow`, `odin` |
| Token prices / market data | `muninn` (internal/service/token) | `swell`, `helios`, ClickHouse |
| Twitter/mindshare data | `argus` | `heimdall` (crawler), `muninn` (display) |
| Sandbox / code execution | `bifrost` | `urania`, `muninn` (crypto agent) |
| Enterprise / B2B API | `huginn` | `muninn` (upstream AI) |
| On-chain data missing | `swell` (ETH), `helios` (SOL) | `diver`, ClickHouse tables |
| Deployment failures | `gitops` / `gitops-stg` | `bifrost` (sandbox deploys) |
| RPC errors / timeouts | `pluto` | Upstream RPC provider configs |
| Address/entity labeling | `recon` | Arkham API, CEX deposit data |

## Key Dependencies

```
muninn ──gRPC──► argus (tweet analytics)
muninn ──gRPC──► odin-flow (AI workflows)
argus  ──gRPC──► muninn (project metadata)    # bidirectional
heimdall ──Kinesis──► argus (raw tweet stream)
swell ──ClickHouse──► muninn/diver (decoded chain data)
helios ──ClickHouse──► muninn/diver (Solana data)
bifrost ◄──HTTP── muninn/urania (deploy requests)
pluto ◄──HTTP── all services (RPC proxy)
proto ──imported── all Go services (gRPC definitions)
```

## Shared Patterns

All Go backend services (`muninn`, `hermod`, `huginn`, `argus`, `bifrost`, `pluto`) share:
- **Cobra CLI** with modes: `api`, `task`, `cron`, `dev`
- **Ent ORM** with read/write PostgreSQL separation
- **Redis** for caching and rate limiting
- **toolkit-v2** shared library for logging, config (Nacos/Viper), health checks
- **gRPC via nirvana** (proto repo) for inter-service communication
- **DataDog** for monitoring and tracing

## Reference Files

| Need | Reference |
|------|-----------|
| Detailed repo descriptions and what each service owns | [service-details.md](references/service-details.md) |
| How to update this skill when repos change | [update-guide.md](references/update-guide.md) |

## Not Surf (Excluded)

These repos are active but belong to Cyber/CyberConnect or Link3, not Surf:
- **Cyber/CC**: `thor`, `hades`, `heracles`, `balder`, `phantasos`, `hermes`, `demeter`, `rhea`, `ladon`, `cyber-frontend`, `cyber-air`, `cybercontracts`, `cybergraph`, `cyberid`
- **Link3**: `link3`, `link3-web-v2`, `link3-notification-tg-bot`, `link3-org-verify-bot`, `nox-backend`
