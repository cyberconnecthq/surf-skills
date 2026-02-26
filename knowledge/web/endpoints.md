# Web Data — Endpoint Reference

<!-- Hermod /v1/web/* — standardized web data endpoints -->

## Endpoints

All endpoints are under `/v1/web/`. Response envelope: `{"data": [...], "meta": {...}}`.

| Endpoint | Description | Key Params | Cost |
|----------|-------------|------------|------|
| `POST /fetch` | Fetch and parse a URL | body (required) | 1 credit |
| `GET /search` | Search the web | `q` (required), `limit`, `site` | 1 credit |

