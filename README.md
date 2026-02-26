# surf-core

Agent Skills for Crypto data access via the Hermod API Gateway. Follows the [Agent Skills Open Standard](https://github.com/anthropics/agent-skills) — works with Claude Code, OpenAI Codex, GitHub Copilot, Gemini CLI, and other agent platforms.

## Repository Structure

```
surf-core/
├── knowledge/          # Domain knowledge (endpoints, patterns, responses)
│   ├── auth/           # Authentication & session docs
│   ├── market/         # Market data (prices, futures, options, indicators)
│   ├── project/        # Project data (overview, TVL, revenue, fees)
│   ├── token/          # Token data (holders, transfers, flows)
│   ├── wallet/         # Wallet data (balance, holdings, tx history)
│   ├── social/         # Social & X/Twitter data (sentiment, users, tweets)
│   ├── news/           # News data (search, feed, AI summaries)
│   ├── web/            # Web data (search, fetch)
│   └── onchain/        # On-chain SQL (ClickHouse databases)
├── runtimes/           # Executable skill implementations
│   ├── cli/            # Bash CLI skills
│   │   ├── lib/        # Shared utilities (config.sh, http.sh)
│   │   ├── login/      # Google Sign-In, session management
│   │   ├── hermod-api/ # Fetch, cache, query Hermod OpenAPI specs
│   │   ├── market/     # Market data — prices, charts, exchanges
│   │   ├── news/       # Crypto news search with semantic ranking
│   │   ├── onchain/    # OnchainSQL — query on-chain data via ClickHouse
│   │   ├── project/    # Project data — overview, TVL, revenue, fees
│   │   ├── token/      # Token data — holders, transfers, exchange flows
│   │   ├── wallet/     # Wallet data — balances, holdings, tx history
│   │   └── social/     # Social & X/Twitter — search, users, tweets
│   └── http/           # HTTP-based skill implementations
│       └── market/     # Market data via HTTP
├── CLAUDE.md
├── README.md
└── SKILL-SPEC.md
```

## Setup

```bash
# Install all skills
npx skills add cyberconnecthq/surf-core --global --all

# Or symlink for development
git clone git@github.com:cyberconnecthq/surf-core.git
ln -s /path/to/surf-core ~/.claude/skills/surf-core
```

## Quick Start

```bash
# 1. Login (one-click Google Sign-In)
runtimes/cli/login/scripts/surf-session login

# 2. Get BTC price
runtimes/cli/market/scripts/surf-market price --ids bitcoin --vs usd

# 3. Check Vitalik's wallet
runtimes/cli/wallet/scripts/surf-wallet balance --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# 4. Search social/X for crypto discussions
runtimes/cli/social/scripts/surf-social search --query "ethereum ETF"

# 5. Explore all 273 API endpoints
runtimes/cli/hermod-api/scripts/surf-api sync
runtimes/cli/hermod-api/scripts/surf-api search holders
```

## Architecture

```
User / Agent
    │
    ├── runtimes/cli/login (Google OAuth → JWT session)
    │
    ├── runtimes/cli/*  skills (CLI wrappers)
    │       │
    │       └── runtimes/cli/lib/ (config.sh + http.sh)
    │               │
    │               └── curl + Bearer token
    │                       │
    ▼                       ▼
~/.surf-core/        Hermod Gateway (api.stg.ask.surf)
session.json              │
                          ├── JWT verification
                          ├── Credit deduction
                          └── Reverse proxy → upstream APIs
                              (CoinGecko, DeBank, Moralis, etc.)
```

Session is stored at `~/.surf-core/session.json`. Login once, auto-refresh for 30 days.

## Knowledge

The `knowledge/` directory contains domain-specific documentation organized by data category. Each subdirectory includes endpoint references, usage patterns, and example responses that agents can use for context.
