# Hermod Authentication Architecture

## Request Flow

```
Client Request
  │
  │  Authorization: Bearer <JWT>
  │
  ▼
Hermod Gateway
  │
  ├─ 1. JWT Verification
  │     - Algorithm: RS256 (RSA-SHA256)
  │     - Verify signature with RSA public key
  │     - Check token not expired (exp claim)
  │     - Extract user_id from payload
  │
  ├─ 2. User Plan Lookup
  │     - Query UserPlan table by user_id
  │     - Determine plan_type (UNLIMITED, BASIC, etc.)
  │
  ├─ 3. Credit Check & Deduction
  │     ├─ UNLIMITED plan → skip balance check, record usage only
  │     └─ Other plans → verify sufficient balance → atomic deduct → record usage
  │
  └─ 4. Reverse Proxy
        - Strip original Authorization header
        - Inject upstream API key (per endpoint config)
        - Forward request to upstream service
        - Return response to client
```

## JWT Structure

**Header:**
```json
{
  "alg": "RS256",
  "typ": "JWT"
}
```

**Payload:**
```json
{
  "user_id": "00000000-0000-0000-0000-000000000099",
  "deploy_id": null,
  "ssid": null,
  "exp": 1772001600
}
```

| Field | Type | Description |
|-------|------|-------------|
| user_id | UUID | Required. Hermod uses this to look up plan and credits |
| deploy_id | UUID or null | Optional. Set when request comes from a bifrost deployment |
| ssid | UUID or null | Optional. Sandbox session ID for agent sessions |
| exp | int | Required. Unix timestamp for token expiration |

## Environments

| Environment | Hermod URL |
|-------------|-----------|
| Production | `https://api.asksurf.ai/gateway` |
| Staging | `https://api.stg.ask.surf/gateway` |

## Credit System

- Each API call costs credits (1-5 per request, varies by endpoint)
- Credits are deducted atomically per request
- UNLIMITED plans bypass balance checks but still record usage
- Credit usage is logged with: endpoint, path, method, cost, balance before/after

## Security Notes

- Client only needs the JWT — never handles API keys for upstream services
- Hermod injects upstream API keys server-side (header, query param, bearer, or path)
- Original JWT is stripped before forwarding to prevent token leakage
- All requests are rate-limited per client IP
- Request body max size: 10MB
- Query string max length: 8,192 characters
