# News Data — Endpoint Reference

<!-- Hermod /v1/news/* — standardized news data endpoints -->

## Endpoints

All endpoints are under `/v1/news/`. Response envelope: `{"data": [...], "meta": {...}}`.

| Endpoint | Description | Key Params | Cost |
|----------|-------------|------------|------|
| `GET /ai` | Get AI news | `project_id`, `limit`, `offset` | 1 credit |
| `GET /ai/detail` | Get AI news detail | `id` (required) | 1 credit |
| `GET /feed` | Get news feed | `id` | 1 credit |
| `GET /search` | Search news articles | `q` (required), `limit`, `offset` | 1 credit |
| `GET /top` | Get top news | `metric` (required), `limit` | 1 credit |

### top — Valid Parameter Values

**`metric`**: `recency`, `trending`

