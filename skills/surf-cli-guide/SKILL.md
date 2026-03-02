---
name: surf-cli-guide
description: "Teaches agents how to use the surf CLI for crypto data research — when to use each domain, common workflows, and best practices. Use when an agent needs to fetch crypto data but doesn't know where to start."
tools: ["bash"]
---

# Surf CLI Guide — What to Use and When

`surf` is a CLI that gives you access to 87 crypto data endpoints across 8 domains. This guide teaches you **which domain solves which problem** and how to chain commands for real research tasks.

## Before You Start

```bash
surf-session check          # Verify you're logged in
surf <command> --help       # Get params for any command
```

If not logged in: `surf-session login` (one-time Google SSO, lasts 30 days).

---

## Domain Map — Match Your Problem to a Domain

| You want to... | Domain | Key commands | Cost |
|---|---|---|---|
| Check prices, market cap, trends | **Market** | `market-price`, `market-top`, `market-trending` | 1 |
| Deep-dive a project (metrics, team, funding) | **Project** | `project-overview`, `project-metrics`, `project-funding` | 1 |
| Inspect a token on-chain (holders, transfers) | **Token** | `token-info`, `token-holders`, `token-transfers` | 1 |
| Analyze a wallet (balance, PnL, history) | **Wallet** | `wallet-balance`, `wallet-pnl`, `wallet-tokens` | 1-2 |
| Track social buzz and sentiment | **Social** | `social-sentiment`, `social-search`, `social-tweets` | 1 |
| Read latest crypto news | **News** | `news-feed`, `news-search`, `news-ai` | 1 |
| Search the open web | **Web** | `web-search`, `web-fetch` | 1 |
| Run raw SQL on blockchain data | **Onchain** | `onchain-sql`, `onchain-tx` | 5 |
| Resolve a name/ticker/address to entity | **Entity** | `entity-resolve` | 0 |

---

## 1. Entity — The Starting Point (Free)

**When**: You have a vague input (name, ticker, address) and need to identify the exact project/token.

```bash
# Resolve any crypto name to a canonical entity
surf entity-resolve --q "uni"
# Returns: project_id, name, ticker, chains, addresses

# Batch resolve multiple entities at once
surf entity-resolve-batch <<< '{"queries": ["bitcoin", "0xdAC17F958D2ee523a2206206994597C13D831ec7"]}'
```

**Pro tip**: Always resolve first when the user gives an ambiguous name. "sol" could be Solana, Solend, or Soldex.

## 2. Market — Prices, Trends & Derivatives

**When**: "What's the price of X?", "What's trending?", "Show me market indicators", "How are derivatives doing?"

### Prices & Rankings

```bash
# Current prices (supports multiple assets)
surf market-price --ids bitcoin,ethereum,solana

# Top assets by market cap, volume, or gainers/losers
surf market-top --metric market_cap --limit 20
surf market-top --metric price_change_percentage_24h --limit 10

# What's trending right now
surf market-trending

# Search for assets by keyword
surf market-search --q "layer 2"
```

### Derivatives & Indicators

```bash
# Futures open interest and funding rates
surf market-futures --symbol BTC

# Options data
surf market-options --symbol BTC

# Liquidation data
surf market-liquidation --symbol BTC

# Technical indicators (RSI, MACD, etc.)
surf market-indicator --symbol BTC --indicator rsi

# On-chain valuation metrics (NUPL, MVRV)
surf market-metric --metric nupl
```

### Macro & Prediction

```bash
# ETF flows
surf market-etf

# TGE (token generation events) calendar
surf market-tge

# Community predictions
surf market-prediction
```

## 3. Project — Deep Research

**When**: "Tell me about Uniswap", "Who funded this project?", "What's their TVL?", "Who's on the team?"

```bash
# Start with overview — gets you everything at a glance
surf project-overview --q ethereum

# Specific metrics (TVL, volume, revenue, users)
surf project-metrics --q uniswap --metric tvl

# Funding rounds and investors
surf project-funding --q optimism

# Team members
surf project-team --q arbitrum

# Tokenomics breakdown
surf project-tokenomics --q solana

# Social accounts and links
surf project-social --q aave

# Upcoming events
surf project-events --q polygon

# On-chain contract addresses
surf project-contracts --q uniswap
```

### Discovery & Screening

```bash
# Discover top projects by category
surf project-discover --sector defi --metric tvl --limit 20

# FDV-based discovery
surf project-discover-fdv --sector "layer-1" --limit 10

# Mindshare leaderboard (social attention)
surf project-mindshare-leaderboard --limit 20

# Smart followers analysis (who follows who)
surf project-smart-followers --q chainlink
```

## 4. Token — On-Chain Token Intelligence

**When**: "Who holds this token?", "Show me recent transfers", "When is the next unlock?"

```bash
# Token metadata (name, supply, decimals, contract)
surf token-info --address 0xdAC17F958D2ee523a2206206994597C13D831ec7 --chain ethereum

# Top holders
surf token-holders --address 0x... --chain ethereum --limit 20

# Recent transfers
surf token-transfers --address 0x... --chain ethereum --limit 20

# On-chain metrics (holder count trends, etc.)
surf token-metrics --address 0x... --chain ethereum

# Token unlock schedule
surf token-unlock --q arbitrum

# Top traders for a token
surf token-top-traders --address 0x... --chain ethereum
```

**Note**: Token commands need `--address` (contract) + `--chain`. Use `entity-resolve` to find these first.

## 5. Wallet — Portfolio & Activity Analysis

**When**: "Analyze this wallet", "What does Vitalik hold?", "Is this wallet profitable?"

```bash
# Portfolio balance (total value in USD)
surf wallet-balance --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Individual token holdings
surf wallet-tokens --address 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# PnL analysis (cost 2 credits)
surf wallet-pnl --address 0x...

# Transaction history (cost 2 credits)
surf wallet-history --address 0x...

# NFT holdings
surf wallet-nft --address 0x...

# Wallet labels (exchange, whale, etc.)
surf wallet-labels --address 0x...

# Search wallets by label or tag
surf wallet-search --q "binance"

# Top wallets (whales, top holders)
surf wallet-top --chain ethereum
```

## 6. Social — Crypto Twitter & Sentiment

**When**: "What are people saying about X?", "Is sentiment bullish?", "Find KOL opinions"

```bash
# Sentiment score for a project (bullish/bearish ratio)
surf social-sentiment --q bitcoin

# Search tweets by keyword
surf social-search --q "ethereum ETF approval"

# Get tweets for a specific project
surf social-tweets --q solana --limit 20

# Look up a specific user's profile
surf social-user --handle vitalikbuterin

# Get a user's recent posts
surf social-user-posts --handle coaborin --limit 10

# Find related/similar accounts
surf social-user-related --handle coaborin

# Top KOLs and influencers
surf social-top --limit 20

# Follower geography distribution
surf social-follower-geo --handle binance
```

## 7. News — Headlines & AI Summaries

**When**: "What happened today in crypto?", "Any news about X?", "Summarize recent events"

```bash
# Latest news feed
surf news-feed --limit 10

# Search news by keyword with date range
surf news-search --q "DeFi hack" --sort recency --from 2025-01-01

# AI-generated news summary (great for briefings)
surf news-ai --q ethereum

# Detailed AI analysis on a specific topic
surf news-ai-detail --q "bitcoin halving impact"

# Top/trending news stories
surf news-top
```

## 8. Web — General Search & Fetch

**When**: You need info beyond the crypto-specific endpoints (docs, blog posts, general research).

```bash
# Web search
surf web-search --q "EIP-4844 proto-danksharding spec"

# Fetch and parse a URL into readable text
surf web-fetch --url "https://ethereum.org/en/roadmap/"
```

## 9. Onchain — Raw Blockchain SQL (Advanced, 5 credits)

**When**: You need custom queries that no pre-built endpoint covers. Power tool for on-chain analysis.

```bash
# Run SQL against ClickHouse blockchain tables
surf onchain-sql <<< '{"sql": "SELECT from_address, to_address, value FROM eth_transactions WHERE to_address = lower('\''0x...'\'') ORDER BY block_number DESC LIMIT 10"}'

# Structured query (guided, no raw SQL)
surf onchain-structured-query <<< '{"chain": "ethereum", "type": "token_transfers", "address": "0x...", "limit": 10}'

# Transaction details by hash
surf onchain-tx --hash 0xabc123... --chain ethereum
```

**Supported chains**: Ethereum (1), BSC (56), Polygon (137), Base (8453), Arbitrum (42161), Optimism (10), Cyber (7560).

---

## Common Workflows

### "Research project X for me"

```bash
surf entity-resolve --q "X"                    # 1. Identify the entity (free)
surf project-overview --q "X"                  # 2. Get the full picture
surf project-metrics --q "X" --metric tvl      # 3. Key metrics
surf project-funding --q "X"                   # 4. Investors and rounds
surf social-sentiment --q "X"                  # 5. Community sentiment
surf news-search --q "X" --sort recency        # 6. Recent news
```

### "What's hot in crypto right now?"

```bash
surf market-trending                           # 1. Trending tokens
surf market-top --metric price_change_percentage_24h --limit 10  # 2. Top gainers
surf news-top                                  # 3. Top news stories
surf project-mindshare-leaderboard --limit 10  # 4. Social attention leaders
```

### "Analyze this wallet address"

```bash
surf wallet-balance --address 0x...            # 1. Total portfolio value
surf wallet-tokens --address 0x...             # 2. Token breakdown
surf wallet-pnl --address 0x...                # 3. Profit/loss analysis
surf wallet-history --address 0x...            # 4. Recent activity
surf wallet-labels --address 0x...             # 5. Known labels
```

### "Due diligence on token 0x..."

```bash
surf token-info --address 0x... --chain ethereum      # 1. Token metadata
surf token-holders --address 0x... --chain ethereum    # 2. Holder distribution
surf token-metrics --address 0x... --chain ethereum    # 3. On-chain metrics
surf token-top-traders --address 0x... --chain ethereum # 4. Top traders
surf token-unlock --q "project-name"                   # 5. Unlock schedule
```

---

## Tips & Gotchas

1. **Always resolve first** — Use `entity-resolve` when the user input is ambiguous. It's free.
2. **`--q` vs `--ids`** — Market commands use `--ids` (CoinGecko IDs like "bitcoin"). Project/Social/News use `--q` (search query).
3. **Token needs chain** — `token-*` and `wallet-*` commands often need `--chain` (ethereum, bsc, polygon, base, arbitrum, optimism, solana).
4. **Filter output** — Use `-f body.data` to get just the data array, `-o json` for raw JSON.
5. **Watch credits** — Onchain SQL costs 5 credits per call. Use pre-built endpoints first, fall back to SQL only when needed.
6. **Pagination** — Use `--limit` (max 100) and `--offset` for paging through results.
7. **POST commands** — `onchain-sql` and `entity-resolve-batch` take JSON on stdin via `<<<`.
8. **Check credits** — `surf-session credits` shows your remaining balance.
