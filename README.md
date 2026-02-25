# surf-core

Agent Skills for Crypto data access via the Hermod API Gateway. Follows the [Agent Skills Open Standard](https://github.com/anthropics/agent-skills) — works with Claude Code, OpenAI Codex, GitHub Copilot, Gemini CLI, and other agent platforms.

## Available Skills

| Skill | Description |
|-------|-------------|
| `surf-login` | Login to Hermod via Google Sign-In (prerequisite for all data skills) |
| `surf-hermod-api` | Fetch, cache, and query Hermod OpenAPI specs (273 endpoints) |
| `surf-trading-data` | Crypto trading data — prices, futures, options, liquidations, indicators |
| `surf-wallet-data` | Wallet data — balances, holdings, tx history, address labels |
| `surf-project-data` | Project data — overview, TVL, revenue, fees, active users |
| `surf-token-data` | Token data — holders, transfers, exchange flows |
| `surf-onchain-sql` | OnchainSQL — query on-chain data via ClickHouse |
| `surf-x-data` | X/Twitter data — search tweets, user profiles, timelines |

## Setup

```bash
# Install all skills
npx skills add cyberconnecthq/surf-core --global --all

# Or symlink for development
git clone git@github.com:cyberconnecthq/surf-core.git
ln -s /path/to/surf-core/surf-login ~/.claude/skills/surf-login
ln -s /path/to/surf-core/surf-trading-data ~/.claude/skills/surf-trading-data
# ... etc
```

## Quick Start

```bash
# 1. Login (one-click Google Sign-In)
surf-login/scripts/surf-session login

# 2. Get BTC price
surf-trading-data/scripts/surf-trading price --ids bitcoin --vs usd

# 3. Check Vitalik's wallet
surf-wallet-data/scripts/surf-wallet balance --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# 4. Search X for crypto news
surf-x-data/scripts/surf-x search --query "ethereum ETF"

# 5. Explore all 273 API endpoints
surf-hermod-api/scripts/surf-api sync
surf-hermod-api/scripts/surf-api search holders
```

## Architecture

```
User / Agent
    │
    ├── surf-login (Google OAuth → JWT session)
    │
    ├── surf-*-data skills (CLI wrappers)
    │       │
    │       └── lib/ (config.sh + http.sh)
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
