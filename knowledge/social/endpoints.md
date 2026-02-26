# Social Data — Endpoint Reference

<!-- Hermod /v1/social/* — standardized social data endpoints -->

## Endpoints

All endpoints are under `/v1/social/`. Response envelope: `{"data": [...], "meta": {...}}`.

| Endpoint | Description | Key Params | Cost |
|----------|-------------|------------|------|
| `GET /follower-geo` | Get follower geography | `handle` (required) | 1 credit |
| `GET /search` | Search social content | `q` (required), `limit` | 1 credit |
| `GET /sentiment` | Get sentiment analysis | `id` (required) | 1 credit |
| `GET /top` | Get top social content | `metric` (required), `limit`, `offset` | 1 credit |
| `POST /tweets` | Get tweets by IDs | body (required) | 1 credit |
| `GET /user/{handle}` | Get social user profile | `handle` (required) | 1 credit |
| `GET /user/{handle}/posts` | Get user posts | `handle` (required), `limit` | 1 credit |
| `GET /user/{handle}/related` | Get related accounts | `handle` (required) | 1 credit |

### top — Valid Parameter Values

**`metric`**: `trending`, `engagement`

