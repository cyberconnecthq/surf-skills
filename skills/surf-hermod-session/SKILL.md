---
name: surf-hermod-session
description: Connect to Hermod API Gateway — configure and manage JWT session
tools: ["bash"]
---

# Hermod Session — API Gateway Connection

Configure and manage the Hermod API Gateway session. **This is the prerequisite for all other surf-core skills.** Without a valid session, no data skill can make API calls.

## When to Use

Use this skill **first**, before any other surf-core skill, when:
- Agent is freshly configured and needs to connect to Hermod
- Session token has expired and needs renewal
- Need to verify the current session is still valid
- Need to check credit balance or account status

## How It Works

```
Agent
  │
  │  1. Configure session (JWT token)
  │
  ▼
surf-session configure --token <JWT>
  │
  │  2. Token saved to ~/.surf-core/session.json
  │
  ▼
All other skills auto-load the session
  │
  │  Authorization: Bearer <JWT>
  │
  ▼
Hermod API Gateway
  │
  ├─ Verify JWT (RSA public key)
  ├─ Extract user_id from JWT payload
  ├─ Look up UserPlan in DB
  │   ├─ UNLIMITED → skip balance check, forward request
  │   └─ Other → check balance, deduct credits, forward request
  └─ Reverse proxy to upstream API
```

## CLI Usage

```bash
# Step 1: Configure session with a JWT token
skills/surf-hermod-session/scripts/surf-session configure --token <JWT>

# Optionally set a custom Hermod URL (default: https://api.asksurf.ai/gateway)
skills/surf-hermod-session/scripts/surf-session configure --token <JWT> --url https://api.stg.ask.surf/gateway

# Step 2: Verify the session works (calls /v1/health)
skills/surf-hermod-session/scripts/surf-session check

# View current session info (decoded JWT payload, expiry, Hermod URL)
skills/surf-hermod-session/scripts/surf-session status

# Check credit balance
skills/surf-hermod-session/scripts/surf-session credits

# Remove saved session
skills/surf-hermod-session/scripts/surf-session logout
```

## JWT Token

The JWT is issued by Muninn (the primary API gateway). Its payload structure:

```json
{
  "user_id": "00000000-0000-0000-0000-000000000099",
  "deploy_id": null,
  "ssid": null,
  "exp": 1772001600
}
```

- `user_id` — Hermod uses this to look up the user's plan and credit balance
- `exp` — Expiration timestamp; session must be renewed before this time
- Hermod verifies the JWT signature with an RSA public key; the client never needs to know the plan type

## Session Persistence

Session is saved to `~/.surf-core/session.json`:

```json
{
  "hermod_url": "https://api.asksurf.ai/gateway",
  "hermod_token": "<JWT>"
}
```

All skills auto-load from this file when `HERMOD_TOKEN` is not set in environment. Environment variables always take precedence.

## Typical Agent Onboarding Flow

1. User provides a JWT token (from Muninn or admin)
2. Agent runs `surf-session configure --token <JWT>`
3. Agent runs `surf-session check` to verify connectivity
4. Agent can now use any other surf-core skill freely

See `references/auth.md` for full authentication architecture details.
