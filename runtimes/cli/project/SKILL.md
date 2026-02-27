---
name: surf-project
description: Research crypto projects — overview, TVL, revenue, fees, users, funding, tokenomics, team, mindshare, and rankings
tools: ["bash"]
---

# Project Data — Crypto Project Intelligence

Research any crypto project's fundamentals: overview, on-chain metrics (TVL, revenue, fees, users), funding history, tokenomics, team, mindshare, smart followers, and protocol rankings. All data via the Hermod API Gateway.

## Quick Reference

| Command | Description | Cost |
|---------|-------------|------|
| `search --query uniswap` | Find projects by name | 1 |
| `overview --id ethereum` | Project description, category, website | 1 |
| `metrics --id aave --metric tvl` | Time-series metrics (tvl, revenue, fees, volume, users) | 1 |
| `top --metric tvl` | Ranked project list by metric | 1 |
| `funding --id arbitrum` | Funding rounds, investors, amounts | 1 |
| `tokenomics --id ethereum` | Token supply, distribution, vesting | 1 |
| `token-info --id ethereum` | Token price, market cap, contracts | 1 |
| `team --id ethereum` | Team members and roles | 1 |
| `contracts --id ethereum` | Deployed contract addresses | 1 |
| `events --id ethereum` | Upcoming and past events | 1 |
| `listings --id ethereum` | Exchange listings | 1 |
| `mindshare --id ethereum --timeframe 7d` | Social mindshare over time | 1 |
| `mindshare-leaderboard --id ethereum` | Mindshare vs competitors | 1 |
| `mindshare-by-tag --id ethereum` | Mindshare by narrative tag | 1 |
| `mindshare-geo --id ethereum` | Mindshare by geography | 1 |
| `mindshare-lang --id ethereum` | Mindshare by language | 1 |
| `smart-followers --id ethereum` | Smart follower summary | 1 |
| `smart-followers-members --id ethereum` | List of smart followers | 1 |
| `smart-followers-events --id ethereum` | Smart follower activity | 1 |
| `smart-followers-history --id ethereum` | Smart follower growth | 1 |
| `social --id ethereum` | Social links (Twitter, Discord, etc.) | 1 |
| `tags` | List all project tags/categories | 1 |
| `discover` | Discover new projects | 1 |
| `discover-fdv --id ethereum` | Discover project FDV data | 1 |
| `discover-summary --id ethereum` | Discover project summary | 1 |
| `discover-tweets --id ethereum` | Discover project tweets | 1 |
| `vc-portfolio --id a16z-crypto` | VC firm's portfolio | 1 |

## Common Tasks

### Task: Research a DeFi Protocol

Investigate a protocol's fundamentals, metrics, and team.

```bash
# Step 1: Find the project ID
surf-project search --query uniswap

# Step 2: Get the overview (description, category, website)
surf-project overview --id uniswap

# Step 3: Check on-chain metrics — TVL, revenue, fees
surf-project metrics --id uniswap --metric tvl
surf-project metrics --id uniswap --metric revenue
surf-project metrics --id uniswap --metric fees

# Step 4: Review tokenomics and team
surf-project tokenomics --id uniswap
surf-project team --id uniswap
```

**What to look for:** Compare revenue vs fees to understand fee capture. Check if TVL is growing or declining. Review token distribution for insider concentration.

### Task: Compare Protocols by Key Metrics

Find the top protocols in a category and compare them.

```bash
# Step 1: Get top protocols by TVL
surf-project top --metric tvl

# Step 2: Get top by revenue to find profitable protocols
surf-project top --metric revenue

# Step 3: Compare specific protocols' metrics over time
surf-project metrics --id aave --metric tvl --start 2025-01-01 --end 2025-06-30
surf-project metrics --id compound --metric tvl --start 2025-01-01 --end 2025-06-30
```

**What to look for:** Protocols with high revenue relative to TVL have better capital efficiency. Rising DAU with flat TVL may indicate retail adoption.

**Valid `--metric` values for `top`:** tvl, revenue, fees, dau, developers, pf_ratio, ps_ratio, dex_volume, lending, stablecoins, upcoming_tge, upcoming_airdrop, new_listing

**Valid `--metric` values for `metrics`:** volume, fee, revenue, tvl, users

### Task: Find TGE and Airdrop Opportunities

Discover upcoming token generation events and airdrops.

```bash
# Step 1: Find projects with upcoming TGEs
surf-project top --metric upcoming_tge

# Step 2: Find projects with upcoming airdrops
surf-project top --metric upcoming_airdrop

# Step 3: Research a promising project
surf-project overview --id arbitrum
surf-project funding --id arbitrum
surf-project smart-followers --id arbitrum
```

**What to look for:** Projects with strong VC backing (check funding), growing smart follower counts, and active development. High mindshare before TGE often signals community interest.

### Task: Protocol Health Check

Assess whether a protocol is healthy or declining.

```bash
# Step 1: Check user activity trend
surf-project metrics --id lido --metric users

# Step 2: Check TVL and revenue trends
surf-project metrics --id lido --metric tvl
surf-project metrics --id lido --metric revenue

# Step 3: Check mindshare — is attention growing or fading?
surf-project mindshare --id lido --timeframe 7d

# Step 4: Check smart follower trend
surf-project smart-followers-history --id lido
```

**What to look for:** Declining users + declining TVL = red flag. Growing mindshare with flat metrics may indicate hype without substance. Smart follower growth often leads price action.

### Task: VC Portfolio Analysis

Research what a specific VC firm has invested in.

```bash
# Step 1: Get the VC's portfolio
surf-project vc-portfolio --id a16z-crypto

# Step 2: Deep-dive into a portfolio company
surf-project overview --id uniswap
surf-project funding --id uniswap
surf-project token-info --id uniswap
```

**What to look for:** Look for patterns in the VC's thesis (L1 vs DeFi vs infra). Cross-reference with `funding` to see round sizes and co-investors.

## Cross-Domain Workflows

### Full Due Diligence on a Protocol

Combine project data with social sentiment and on-chain activity for comprehensive analysis.

```bash
# Project fundamentals
surf-project overview --id aave
surf-project metrics --id aave --metric tvl
surf-project metrics --id aave --metric revenue
surf-project funding --id aave
surf-project tokenomics --id aave
surf-project team --id aave

# Social sentiment (use surf-social)
surf-social sentiment --id aave
surf-social search --query "aave" --limit 10

# On-chain DEX activity (use surf-onchain)
surf-onchain sql --sql "SELECT project, count() AS trades, sum(amount_usd) AS volume FROM dex_ethereum.trades WHERE block_time >= today() - 7 AND token_pair LIKE '%AAVE%' GROUP BY project ORDER BY volume DESC LIMIT 10"
```

## Tips

- **`--id` vs `--q`:** Most endpoints support both `--id` (Surf UUID, takes priority) and `--q` (entity name like `ethereum`, `uniswap`). Use `--q` when you have a project name; use `--id` when you have the exact UUID. Only `metrics` requires a Token Terminal slug via `--id`.
- **Metrics time range:** Use `--start` and `--end` (YYYY-MM-DD) with `metrics` to narrow the time window.
- **Large responses:** Use `--limit` on `search` and `top` to control response size. Default varies by endpoint.
- **All output is JSON.** Data goes to stdout, errors to stderr.
- **1 credit per call** for all project endpoints.
