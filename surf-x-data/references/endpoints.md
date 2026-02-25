# X/Twitter Data — Endpoint Reference

Base path: `/gateway/v1/x`

All endpoints require JWT auth (`Authorization: Bearer <token>`).

---

## POST /search

Search tweets on X/Twitter. **Cost: 3 credits.**

**Request Body:**
```json
{
  "query": "bitcoin ETF approval"
}
```

**Response:** Array of tweet objects with text, author, timestamp, engagement metrics.

---

## GET /user/{handle}

Get user profile by handle. **Cost: 2 credits.**

**Path Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| handle | string | yes | X/Twitter handle (without @) |

**Response:** User profile with name, bio, follower count, following count, verified status.

---

## GET /user/{handle}/tweets

Get recent tweets from a user. **Cost: 3 credits.**

**Path Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| handle | string | yes | X/Twitter handle (without @) |

**Response:** Array of recent tweets with text, timestamp, engagement metrics.

---

## POST /tweets

Get specific tweets by IDs. **Cost: 2 credits.**

**Request Body:**
```json
{
  "tweet_ids": ["1234567890", "0987654321"]
}
```

**Response:** Array of tweet objects matching the provided IDs.
