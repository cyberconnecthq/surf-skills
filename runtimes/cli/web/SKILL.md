---
name: surf-web
description: Search the web and fetch page content for crypto research, due diligence, and protocol documentation
tools: ["bash"]
---

# Web Data — Search & Fetch

Search the web and fetch full page content for crypto research, protocol documentation, and due diligence.

## Quick Reference

| Command | Description | Cost |
|---------|-------------|------|
| `search` | Web search with optional site filter | 1 credit |
| `fetch` | Fetch and parse a URL into readable content | 1 credit |

## Common Tasks

### Task: Research a protocol or project
Find documentation, official sites, and technical details.
```bash
# Search for protocol documentation
runtimes/cli/web/scripts/surf-web search --query "ethereum roadmap 2026" --limit 5

# Search for a DeFi protocol
runtimes/cli/web/scripts/surf-web search --query "aave v3 documentation" --limit 5

# Search for a new L2 chain
runtimes/cli/web/scripts/surf-web search --query "base chain developer docs" --limit 3

# Fetch the actual page content for deep reading
runtimes/cli/web/scripts/surf-web fetch --url https://ethereum.org/roadmap
```
**What to look for:** Official documentation URLs (.org, .io domains), GitHub repos, and audit reports. Use `fetch` to read full page content after finding relevant URLs via `search`.

### Task: Search within a specific site
Use the `--site` filter to restrict results to trusted sources.
```bash
# Search only CoinDesk
runtimes/cli/web/scripts/surf-web search --query "ethereum" --site coindesk.com --limit 3

# Search only CoinTelegraph
runtimes/cli/web/scripts/surf-web search --query "bitcoin regulation" --site cointelegraph.com --limit 3

# Search only a project's docs
runtimes/cli/web/scripts/surf-web search --query "lending pools" --site docs.aave.com --limit 3

# Search DeFi Llama for TVL data
runtimes/cli/web/scripts/surf-web search --query "total value locked" --site defillama.com --limit 3
```
**What to look for:** Site-filtered searches are useful when you need information from a specific trusted source. Combine with `fetch` to read the full article.

### Task: Fetch and read a specific page
Parse any URL into clean, readable text content.
```bash
# Read a protocol's homepage
runtimes/cli/web/scripts/surf-web fetch --url https://ethereum.org

# Read a specific documentation page
runtimes/cli/web/scripts/surf-web fetch --url https://docs.aave.com/hub

# Read a blog post or article
runtimes/cli/web/scripts/surf-web fetch --url https://vitalik.eth.limo
```
**What to look for:** The `content` field contains the full parsed page text. The `title` and `url` fields confirm you fetched the right page. Use this to extract specific data points, quotes, or technical specifications.

### Task: Due diligence on a new project
Investigate a project's legitimacy and technical foundation.
```bash
# 1. Find the project's official presence
runtimes/cli/web/scripts/surf-web search --query "projectname crypto official site" --limit 5

# 2. Look for audit reports
runtimes/cli/web/scripts/surf-web search --query "projectname smart contract audit" --limit 3

# 3. Check for team information
runtimes/cli/web/scripts/surf-web search --query "projectname team founders" --limit 3

# 4. Read the documentation
runtimes/cli/web/scripts/surf-web fetch --url https://docs.projectname.io
```
**What to look for:** Verified audit reports from firms like Trail of Bits, OpenZeppelin, Certik. Active GitHub repositories. Team members with verifiable backgrounds. Red flags: anonymous team with no audits, copied documentation, no GitHub activity.

## Cross-Domain Workflows

### Comprehensive Protocol Research
Combine web data with news and market data for full analysis.
```bash
# 1. Web search for protocol overview
runtimes/cli/web/scripts/surf-web search --query "lido staking protocol" --limit 3

# 2. Fetch documentation for details
runtimes/cli/web/scripts/surf-web fetch --url https://docs.lido.fi

# 3. Get recent news (use surf-news)
runtimes/cli/news/scripts/surf-news search --query "lido staking" --limit 5

# 4. Check token price and market data (use surf-market)
runtimes/cli/market/scripts/surf-market price --ids lido-dao --vs-currencies usd
runtimes/cli/market/scripts/surf-market indicator --name rsi --symbol LDO/USDT
```

### Verify a Claim or Rumor
Fact-check information circulating in crypto communities.
```bash
# 1. Search for the claim
runtimes/cli/web/scripts/surf-web search --query "claim or rumor text here" --limit 5

# 2. Check reputable news sources
runtimes/cli/web/scripts/surf-web search --query "claim" --site coindesk.com --limit 3
runtimes/cli/web/scripts/surf-web search --query "claim" --site theblock.co --limit 3

# 3. Cross-reference with news database (use surf-news)
runtimes/cli/news/scripts/surf-news search --query "claim keywords" --limit 5
```

## Tips
- All output is JSON. Data goes to stdout, errors to stderr.
- Use `--limit` to control the number of search results. Start with 3-5 to save context window.
- The `--site` filter is powerful for restricting searches to specific domains (docs, news sites, explorers).
- `fetch` returns the full page text in the `content` field, which can be large. Use it selectively.
- Search results include `title`, `url`, and `description`. Often the description is enough without fetching.
- Combine `search` to find URLs, then `fetch` to read specific pages in detail.
- Run `--check-setup` to verify your API credentials before first use.
