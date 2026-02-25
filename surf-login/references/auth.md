# Hermod Authentication Architecture

## Login → Session → API Call Flow

```
User
  │
  ├─ Google OAuth (Browser) ───────────────────────────────┐
  │   1. surf-session login → opens browser                │
  │   2. User clicks Google account                        │
  │   3. Browser sends credential to local server          │
  │   4. POST /muninn/v2/auth/oauth/google                 │
  │      {"credentials": "<google_id_token>"}              │
  │   → {"data": {"access_token":"...","refresh_token":"..."}}
  │                                                        │
  ▼                                                        │
~/.surf-core/session.json  ◄───────────────────────────────┘
  │  hermod_token (access_token, 1h)
  │  refresh_token (30d)
  │
  ▼
surf-core Skills (surf-trading, surf-wallet, etc.)
  │
  │  Authorization: Bearer <access_token>
  │  (auto-refresh if <5min remaining)
  │
  ▼
Hermod Gateway
  │
  ├─ 1. JWT Verification (RS256 with RSA public key)
  ├─ 2. User Plan Lookup (by user_id from JWT sub claim)
  ├─ 3. Credit Check & Deduction
  └─ 4. Reverse Proxy → Upstream API (inject API keys server-side)
```

## Muninn Auth Endpoints (V2)

Base URL: `https://api.stg.ask.surf/muninn`

### POST /v2/auth/oauth/google
Login with Google OAuth ID token.

Request:
```json
{"credentials": "<google_id_token>", "platform": "WEB"}
```

Response:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "uuid",
    "is_registered": false,
    "from_invitation": false
  }
}
```

### POST /v2/auth/refresh
Refresh access token.

Request:
```json
{"refresh_token": "uuid-from-login"}
```

Response:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...(new)",
    "refresh_token": "uuid (same, expiry extended)"
  }
}
```

## Token Lifetimes

| Token | Lifetime | Storage |
|-------|----------|---------|
| access_token | 1 hour | JWT (stateless) |
| refresh_token | 30 days | DB (revocable) |

## JWT Payload

```json
{
  "sub": "user-uuid",
  "iss": "https://asksurf.ai",
  "aud": ["https://asksurf.ai"],
  "iat": 1740000000,
  "exp": 1740003600
}
```

Hermod uses the `sub` claim to look up user plan and credit balance.

## Auto-Refresh Logic

`lib/config.sh` runs on every skill invocation:

1. Load `access_token` from session file
2. Decode JWT, check `exp` claim
3. If expires within 5 minutes and `refresh_token` exists:
   - Call `POST /muninn/v2/auth/refresh`
   - Update session file with new `access_token`
4. Proceed with API call using valid token

This means a user only needs to login once every 30 days.

## Credit System

- Each API call costs credits (1-5 per request, varies by endpoint)
- Credits are deducted atomically per request
- UNLIMITED plans bypass balance checks but still record usage

## Security Notes

- Client only needs the JWT — never handles upstream API keys
- Hermod injects upstream API keys server-side
- Original JWT is stripped before forwarding to prevent token leakage
- Session file is chmod 600 (owner-only)
- Refresh tokens are stored in Muninn DB and can be revoked server-side
