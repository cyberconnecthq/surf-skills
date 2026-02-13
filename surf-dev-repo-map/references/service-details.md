# Service Details

Detailed descriptions of each Surf repo, what it owns, and what it talks to.

## Backend Services

### muninn — Main Surf Backend API

The central hub of the Surf app. Handles everything user-facing.

**Owns:**
- User auth (Google OAuth, Apple OAuth, email OTP, JWT)
- Chat/AI (WebSocket + SSE streaming, sessions, folders, audio transcription)
- Crypto agent (code-gen AI with sessions, file uploads, artifacts, live preview)
- Project data (trending, mindshare, smart follower analytics)
- Token data (market data, sparklines, candles, events, liquidation, unlocks)
- News (AI-generated feed, search, notifications)
- Subscriptions (Stripe, Daimo, RevenueCat)
- Watchlists, wallets, referrals, campaigns, TGE tracking

**Talks to:**
- `argus` (gRPC) — tweet/mindshare data
- `odin-flow` (gRPC) — AI workflows
- PostgreSQL (read/write split via Ent ORM)
- Redis (caching, rate limiting, distributed locks)
- AWS SQS, S3, DynamoDB, SES

**Port:** 8080 (REST + Swagger) + gRPC + health server

---

### hermod — New API Gateway

Scaffolded from muninn. Being built out as an additional API gateway for Surf.

**Key differences from muninn:**
- API base path: `/gateway` (vs `/muninn`)
- DB name: `hermod` (vs `odin`)
- Skeleton Ent schemas (add as needed)
- No gRPC yet

**Port:** 8080 (REST + Swagger) + health at :4012

---

### huginn — Enterprise/B2B API Gateway

Multi-tenant platform for external partners (e.g., Bithumb) to access Surf's AI.

**Owns:**
- Chat completions proxy (`/v1/chat/completions`)
- Market intelligence APIs (must-know news, sentiment, trends, reports)
- Tenant management (registration, API keys, usage)
- Billing/credits (monthly refresh, usage tracking, low-credit alerts)

**Talks to:**
- PostgreSQL (tenants, API keys, credits, usage history)
- Redis (rate limiting, caching)
- Upstream AI services (proxied completions)
- AWS SES (email alerts)

**Port:** 8080 (REST at `/surf-ai/` + Swagger)

---

### argus — Twitter/X Data Engine

Real-time tweet ingestion and analytics.

**Owns:**
- Tweet ingestion (KCL workers consuming Kinesis streams)
- Project mention detection (Aho-Corasick matching)
- Tweet signal monitoring (noteworthy + FIVE_STAR accounts)
- Mindshare analytics (by geo, language, tag; leaderboards)
- Smart follower analytics (influential account tracking)
- Sentiment analysis (via XAI/Grok)
- Following tracking (Kinesis → DynamoDB → Athena diffs)

**Talks to:**
- `muninn` (gRPC) — fetches project metadata and X account mappings
- PostgreSQL, Redis
- AWS Kinesis (tweet + following streams)
- AWS DynamoDB (`argus-core-followers`)
- AWS SQS, Athena + S3
- XAI/Grok API, DataDog

**Modes:** `api` (gRPC server), `task` (KCL workers), `cron` (scheduled jobs), `dev`

---

### bifrost — Deployment Orchestrator

Bridges sandbox builds to Kubernetes. Named after the Norse rainbow bridge.

**Owns:**
- Deploy S3 artifacts → K8s Deployment + Service (security-hardened pods)
- Scale management (replicas, resource limits)
- JWT token generation for Data API Gateway auth
- Reconciler (30s sync loop: DB ↔ K8s state)
- Pod watcher (SharedInformer for real-time events)
- Token janitor (hourly cleanup of expired tokens)

**Talks to:**
- PostgreSQL (deployment + token state)
- Kubernetes/EKS (`deployed-apps` namespace)
- S3 (artifact fetching)
- Istio (routing via VirtualService at `{app}.apps.stg.ask.surf`)

**Port:** 8080 (HTTP) + 9090 (gRPC). Modes: `api`, `task`

---

### pluto — Internal RPC Proxy

JSON-RPC proxy and load balancer for EVM chains.

**Owns:**
- JSON-RPC proxying (standard Ethereum methods)
- Weighted endpoint selection with failover
- Endpoint health monitoring (refresh/recover crons)
- Usage statistics (→ SQS for analytics)

**Talks to:**
- External EVM RPC providers (multi-chain, dynamically managed)
- PostgreSQL (endpoint configs, RPC records)
- AWS SQS (usage stats)

**Port:** 8080 (JSON-RPC POST `/`)

---

### proto — Shared Protobuf Definitions

**Not a running service.** Contains `.proto` files and generated Go code for all inter-service gRPC communication.

- Defines services for: argus, balder, demeter, exactly, hades, heracles, hermes, ladon, link3, muninn, odin-flow, rhea, thor
- Uses `buf` for breaking change detection
- Services register in Nacos: `service_grpc_config_{name}`

---

## AI / Search

### odin — Core Search Engine

The "search for knowledge" engine powering Surf's AI features. Python-based.

### odin-flow — Workflow Orchestration

AI workflow orchestration service. Called by muninn over gRPC to handle multi-step AI tasks.

### urania — Coding Agent

Coding agent with data_frame calculation capabilities. Works with bifrost for sandbox execution.

### recon — Onchain Intelligence

**Go API server** that proxies Arkham Intelligence API through rotating proxies, with local database cache. Includes:
- Entity lookup and address enrichment across chains
- Custom HMAC-based Arkham API signing
- Python crawler component for entity graph expansion
- CEX deposit address database (30+ exchanges)
- Custom address clustering algorithms

---

## Data / Pipeline

### swell — Ethereum Data Pipeline

Massive ETH data pipeline: BigQuery → GCS → ClickHouse → dbt.
- **Scale:** 6.1B event logs, 3.2B transactions, 14.7B traces
- **Protocols:** 75+ decoded (32 DEX, 23 bridge, 16 lending, 4 staking)
- **Prediction markets:** Polymarket (on-chain) + Kalshi (REST API)
- **Verification:** Cross-checked against Dune Analytics
- **Orchestration:** Dagster

### helios — Solana Data Pipeline

Solana blockchain data indexing into ClickHouse, replicating Dune's Solana dataset. Python-based.

### heimdall — Twitter/X Crawler

Distributed crawl service feeding data into argus:
- Multi-account pool with rotation (Redis-backed)
- Crawls: tweets, retweets, replies, followers, followings, search, engagement
- Incremental crawling with checkpoint/resume
- SQS task queue → Kinesis data stream output
- FastAPI server for task submission
- Internally called "TwitterCrawlerWhite"

### diver — Data Analysis

TypeScript-based data analysis tools for the Surf platform.

### token-monitoring — Token Monitoring

Token price and volume monitoring service.

---

## Infra / DevOps

### gitops / gitops-stg — GitOps Deployment

ArgoCD-based GitOps for production and staging deployments. Changes to these repos trigger deployments.

### dagster-staging — Dagster Orchestration

Dagster pipeline orchestration for staging environment. Coordinates data pipeline runs.

### OTS — External Dependencies

GitOps configuration for deploying external dependencies (third-party tools, databases, etc.).
