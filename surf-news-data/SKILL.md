---
name: surf-news-data
description: Search crypto news articles with semantic ranking and recency boosting
tools: ["bash"]
---

# News Data — Crypto News Search

Search crypto news articles via the Hermod API Gateway. Uses OpenSearch with semantic multi-field matching (project, title, summary, content) and Gaussian time-decay ranking for recency boosting.

## When to Use

Use this skill when you need to:
- Search for latest crypto news on a topic (e.g. "bitcoin ETF", "solana defi hack")
- Find news about a specific project (e.g. Ethereum, Uniswap)
- Get news from a specific source (e.g. COINDESK, DECRYPT)
- Look up news within a specific time range
- Get context for market events and price movements

## CLI Usage

```bash
# Check setup
surf-news-data/scripts/surf-news --check-setup

# Basic search (default: 5 results, sorted by relevance + recency)
surf-news-data/scripts/surf-news search --query "bitcoin ETF"

# Limit results
surf-news-data/scripts/surf-news search --query "solana defi" --limit 3

# Paginate (offset-based)
surf-news-data/scripts/surf-news search --query "ethereum" --limit 5 --offset 0
surf-news-data/scripts/surf-news search --query "ethereum" --limit 5 --offset 5

# Filter by project name
surf-news-data/scripts/surf-news search --query "price" --project Ethereum --limit 3

# Filter by source
surf-news-data/scripts/surf-news search --query "bitcoin" --source COINDESK --limit 3

# Filter by time range (unix timestamps)
surf-news-data/scripts/surf-news search --query "bitcoin" --from 1771900000 --to 1772030000 --limit 3

# Combine filters
surf-news-data/scripts/surf-news search --query "hack" --project Solana --source DECRYPT --limit 5
```

## Important Notes

- **`--query` is required** — semantic search across title, summary, content, and project name.
- **Use `--limit`** — default is 5. Larger values return more JSON. Max varies by backend.
- **Pagination**: Use `--offset` to paginate. `--offset 0 --limit 5` = page 1, `--offset 5 --limit 5` = page 2.
- **`--project`**: Filters by `project_name` field (e.g. `Bitcoin`, `Ethereum`, `Solana`, `Uniswap`). Case-sensitive.
- **`--source`**: Known sources include `COINDESK`, `DECRYPT`, `BLOCKBEATS`, `TRADINGVIEW`, `PHEMEX`, `CHAINCATCHER`, `COINPAPER`, `PANEWS`, etc.
- **`--from` / `--to`**: Unix timestamps (seconds). Use for time-range filtering.
- **Ranking**: Results are ranked by semantic relevance with Gaussian time-decay on `published_at` — recent articles rank higher.
- **Response fields**: Each article has `title`, `summary`, `content`, `url`, `source`, `project_name`, `published_at` (unix timestamp).

## Cost

- search: 1 credit

## Endpoints Reference

See `references/endpoints.md` for full parameter details and response formats.
