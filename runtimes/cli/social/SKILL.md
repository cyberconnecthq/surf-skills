---
name: surf-social
description: Analyze crypto social sentiment, research KOLs, track narratives, and search X/Twitter content
tools: ["bash"]
---

# Social Data — Crypto Social & X/Twitter Intelligence

Search X/Twitter content, analyze project sentiment, research KOL profiles, track trending narratives, and explore follower demographics. All data via the Hermod API Gateway.

## Quick Reference

| Command | Description | Cost |
|---------|-------------|------|
| `search --query "bitcoin" --limit 10` | Search tweets by keyword | 1 |
| `sentiment --id ethereum` or `--q ethereum` | Sentiment score for a project | 1 |
| `user --handle vitalikbuterin` | KOL profile (bio, followers, following) | 1 |
| `user-posts --handle vitalikbuterin --limit 10` | Recent posts from a user | 1 |
| `user-related --handle vitalikbuterin` | Related/similar accounts | 1 |
| `follower-geo --id <uuid>` or `--q bitcoin` | Follower geography breakdown | 1 |
| `top --metric trending --limit 10` | Trending social content | 1 |
| `top --metric engagement --limit 10` | Top content by engagement | 1 |
| `tweets --ids '["1880293339000000000"]'` | Fetch specific tweets by ID | 1 |

## Common Tasks

### Task: Gauge Sentiment Around a Project

Check what people are saying and how they feel about a project.

```bash
# Step 1: Get the sentiment score
surf-social sentiment --id ethereum

# Step 2: Search recent tweets to see what people are discussing
surf-social search --query "ethereum" --limit 10

# Step 3: Check trending content for broader context
surf-social top --metric trending --limit 10
```

**What to look for:** Sentiment score gives a quantitative signal. Scan tweet content for recurring themes (upgrade hype, security concerns, competitor comparisons). High engagement on negative tweets is a stronger bearish signal than low-engagement complaints.

### Task: Research a KOL (Key Opinion Leader)

Build a profile of an influential crypto figure.

```bash
# Step 1: Get their profile
surf-social user --handle CryptoHayes

# Step 2: Read their recent posts
surf-social user-posts --handle CryptoHayes --limit 20

# Step 3: Find related accounts (who they're connected to)
surf-social user-related --handle CryptoHayes

# Step 4: Check where their followers are from (use --q for name-based lookup)
surf-social follower-geo --q CryptoHayes
```

**What to look for:** Follower count vs engagement ratio reveals real influence. Related accounts show their network. Geography data helps assess regional bias. Scan posts for consistent shilling patterns or genuine analysis.

### Task: Track Narrative Momentum

Identify which crypto narratives are gaining traction.

```bash
# Step 1: Check what's trending now
surf-social top --metric trending --limit 20

# Step 2: Search for specific narrative keywords
surf-social search --query "RWA tokenization" --limit 10
surf-social search --query "restaking" --limit 10
surf-social search --query "AI agents" --limit 10

# Step 3: Compare engagement across narratives
surf-social top --metric engagement --limit 20
```

**What to look for:** Narratives appearing repeatedly in trending content are gaining momentum. Compare tweet volume and engagement across narratives. Early-stage narratives (few tweets, rising engagement) offer the best risk/reward.

### Task: Monitor a Specific Event or Announcement

Track social reaction to a protocol event (hack, upgrade, token launch).

```bash
# Step 1: Search for event-specific keywords
surf-social search --query "uniswap v4 launch" --limit 20

# Step 2: Check project sentiment before and after
surf-social sentiment --id uniswap

# Step 3: See if KOLs are commenting
surf-social search --query "uniswap" --limit 20
```

**What to look for:** Rapid spike in tweet volume signals awareness. Sentiment shift after an event reveals market interpretation. KOL commentary often sets the narrative direction.

## Cross-Domain Workflows

### Sentiment-Price Divergence Analysis

Combine social sentiment with market data to find potential mispricings.

```bash
# Social sentiment
surf-social sentiment --id ethereum
surf-social search --query "ethereum" --limit 10

# Market data (use surf-market)
surf-market price --ids ethereum --vs usd

# Project fundamentals (use surf-project)
surf-project metrics --id ethereum --metric users
surf-project mindshare --id ethereum --timeframe 7d
```

**What to look for:** Positive sentiment + declining price = potential buy signal (crowd is bullish but price hasn't caught up). Negative sentiment + rising price = potential distribution phase. Always cross-check with on-chain activity.

### KOL Portfolio Mapping

Map what a KOL is talking about to find their likely positions.

```bash
# KOL recent posts
surf-social user-posts --handle vitalikbuterin --limit 20

# Research the projects they mention
surf-project search --query "mentioned_project"
surf-project overview --id mentioned_project
```

## Tips

- **`--id`/`--q` vs `--handle`:** Use `--id` (UUID) or `--q` (name) for entity-resolved endpoints (`sentiment`, `follower-geo`). Use `--handle` for X/Twitter usernames (e.g., `vitalikbuterin`, `CryptoHayes`) in `user`, `user-posts`, `user-related`.
- **`--metric` for `top`:** Valid values are `trending` and `engagement`.
- **Tweet search returns X/Twitter posts.** Results include tweet text, author info, and engagement stats (views, likes, reposts, replies).
- **All output is JSON.** Data goes to stdout, errors to stderr.
- **Use `--limit`** to control response size on `search`, `top`, and `user-posts`.
- **1 credit per call** for all social endpoints.
