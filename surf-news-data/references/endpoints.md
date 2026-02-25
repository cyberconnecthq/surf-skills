# News Data — Endpoints Reference

## POST /gateway/v1/news/search

Search crypto news articles using semantic search with time-decay ranking.

### Request Body (JSON)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| query | string | yes | Search text — matched against project_name, title, summary, content |
| limit | integer | no | Max results to return (default: 5) |
| offset | integer | no | Skip N results for pagination (default: 0) |
| project_name | string | no | Filter by project name (e.g. "Bitcoin", "Ethereum") |
| source | string | no | Filter by news source (e.g. "COINDESK", "DECRYPT") |
| from_time | integer | no | Filter: published_at >= this unix timestamp |
| to_time | integer | no | Filter: published_at <= this unix timestamp |

### Response

```json
{
  "success": true,
  "data": {
    "articles": [
      {
        "id": "",
        "title": "Article title",
        "summary": "Short summary of the article",
        "content": "Full article text",
        "url": "https://example.com/article",
        "source": "COINDESK",
        "project_name": "Bitcoin",
        "published_at": 1771995742
      }
    ],
    "total": 10000
  }
}
```

### Known Sources

BLOCKBEATS, CHAINCATCHER, COINDESK, COINPAPER, COINSPEAKER, CRYPTONEWS, DECRYPT, GLOBENEWSWIRE, PANEWS, PHEMEX, TRADINGVIEW, and more.

### Ranking

Uses OpenSearch `function_score` with:
- `multi_match` on fields: project_name, title, summary, content
- Gaussian decay on `published_at` for recency boosting (recent articles score higher)
