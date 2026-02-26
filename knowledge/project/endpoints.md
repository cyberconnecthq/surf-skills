# Project Data — Endpoint Reference

<!-- Hermod /v1/project/* — standardized project data endpoints -->

## Endpoints

All endpoints are under `/v1/project/`. Response envelope: `{"data": [...], "meta": {...}}`.

| Endpoint | Description | Key Params | Cost |
|----------|-------------|------------|------|
| `GET /contracts` | Get project contracts | `id` (required) | 1 credit |
| `GET /discover` | Discover projects |  | 1 credit |
| `GET /discover/fdv` | Get discover project FDV | `id` (required) | 1 credit |
| `GET /discover/summary` | Get discover project summary | `id` (required) | 1 credit |
| `GET /discover/tweets` | Get discover project tweets | `id` (required) | 1 credit |
| `GET /events` | Get project events | `id` (required), `type` | 1 credit |
| `GET /funding` | Get project funding history | `id` (required) | 1 credit |
| `GET /listings` | Get project exchange listings | `id` (required) | 1 credit |
| `GET /metrics` | Get project metrics | `id` (required), `metric` (required), `start`, `end`, `chain` | 1 credit |
| `GET /mindshare` | Get project mindshare | `id` (required), `timeframe` | 1 credit |
| `GET /mindshare/by-tag` | Get project mindshare by tag | `id` (required) | 1 credit |
| `GET /mindshare/geo` | Get project mindshare by geography | `id` (required) | 1 credit |
| `GET /mindshare/lang` | Get project mindshare by language | `id` (required) | 1 credit |
| `GET /mindshare/leaderboard` | Get project mindshare leaderboard | `id` (required) | 1 credit |
| `GET /overview` | Get project overview | `id` (required) | 1 credit |
| `GET /search` | Search projects | `q` (required), `limit` | 1 credit |
| `GET /smart-followers` | Get project smart followers | `id` (required) | 1 credit |
| `GET /smart-followers/events` | Get project smart followers events | `id` (required) | 1 credit |
| `GET /smart-followers/history` | Get project smart followers history | `id` (required) | 1 credit |
| `GET /smart-followers/members` | Get project smart followers members | `id` (required) | 1 credit |
| `GET /social` | Get project social links | `id` (required) | 1 credit |
| `GET /tags` | Get project tags | `id` | 1 credit |
| `GET /team` | Get project team | `id` (required) | 1 credit |
| `GET /token-info` | Get project token info | `id` (required) | 1 credit |
| `GET /tokenomics` | Get project tokenomics | `id` (required) | 1 credit |
| `GET /top` | Get top/ranked projects | `metric` (required) | 1 credit |
| `GET /vc-portfolio` | Get VC portfolio | `id` (required) | 1 credit |

### metrics — Valid Parameter Values

**`metric`**: `volume`, `fee`, `revenue`, `tvl`, `users`

### mindshare — Valid Parameter Values

**`timeframe`**: `1d`, `7d`, `30d`

### top — Valid Parameter Values

**`metric`**: `tvl`, `revenue`, `fees`, `dau`, `developers`, `pf_ratio`, `ps_ratio`, `dex_volume`, `lending`, `stablecoins`, `upcoming_tge`, `upcoming_airdrop`, `new_listing`

### Chain Support

| Endpoint | Supported Chains |
|----------|-----------------|
| `metrics` | arbitrum |

