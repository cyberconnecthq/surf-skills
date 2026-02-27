#!/usr/bin/env bash
# http.sh — HTTP utilities for surf-core CLI tools
# Provides curl wrappers with unified headers, error handling, and JSON output.
# Safe to source standalone — auto-loads config.sh if HERMOD_URL is not set.

set -euo pipefail

# Auto-load config.sh if not already sourced (enables standalone `source http.sh`)
if [[ -z "${HERMOD_URL:-}" ]]; then
  _HTTP_SH_DIR="$(cd "$(dirname "$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")")" && pwd)"
  if [[ -f "$_HTTP_SH_DIR/config.sh" ]]; then
    source "$_HTTP_SH_DIR/config.sh"
  fi
  unset _HTTP_SH_DIR
fi

# Try to refresh access token using saved refresh_token. Returns 0 on success.
_surf_try_refresh() {
  local session_file="${SURF_SESSION_FILE:-$HOME/.surf-core/session.json}"
  [[ -f "$session_file" ]] || return 1

  local refresh_token
  refresh_token=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('refresh_token',''))" "$session_file" 2>/dev/null) || return 1
  [[ -n "$refresh_token" ]] || return 1

  local muninn_url="${MUNINN_URL:-https://api.stg.ask.surf/muninn}"
  local raw
  raw=$(curl -s --max-time 10 -w "\n%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d "{\"refresh_token\": \"$refresh_token\"}" \
    "${muninn_url}/v2/auth/refresh" 2>/dev/null) || return 1

  local code resp_body
  code=$(echo "$raw" | tail -1)
  resp_body=$(echo "$raw" | sed '$d')
  [[ "$code" -lt 400 ]] || return 1

  local new_token new_refresh
  new_token=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('data',{}).get('access_token',''))" <<< "$resp_body" 2>/dev/null) || return 1
  [[ -n "$new_token" ]] || return 1

  new_refresh=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('data',{}).get('refresh_token',''))" <<< "$resp_body" 2>/dev/null) || new_refresh=""
  : "${new_refresh:=$refresh_token}"

  HERMOD_TOKEN="$new_token"
  python3 -c "
import json, sys
data = {'hermod_url': sys.argv[1], 'hermod_token': sys.argv[2], 'access_token': sys.argv[2], 'refresh_token': sys.argv[3]}
with open(sys.argv[4], 'w') as f:
    json.dump(data, f, indent=2)
" "$HERMOD_URL" "$new_token" "$new_refresh" "$session_file" 2>/dev/null
  echo '{"auto_refresh": true, "message": "Access token refreshed on 401."}' >&2
  return 0
}

# GET request to Hermod API
# Usage: surf_get "/v1/market/price" "ids=bitcoin&vs_currencies=usd"
surf_get() {
  local path="$1"
  local query="${2:-}"
  local url="${HERMOD_URL}${path}"

  if [[ -n "$query" ]]; then
    url="${url}?${query}"
  fi

  local http_code body
  body=$(curl -s --max-time 30 -w "\n%{http_code}" \
    -H "Authorization: Bearer ${HERMOD_TOKEN}" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    "$url" 2>/dev/null) || {
    echo '{"error": "Request failed: network error or invalid URL"}' >&2
    return 1
  }

  http_code=$(echo "$body" | tail -1)
  body=$(echo "$body" | sed '$d')

  # Auto-refresh on 401 and retry once
  if [[ "$http_code" == "401" ]] && _surf_try_refresh; then
    body=$(curl -s --max-time 30 -w "\n%{http_code}" \
      -H "Authorization: Bearer ${HERMOD_TOKEN}" \
      -H "Content-Type: application/json" \
      -H "Accept: application/json" \
      "$url" 2>/dev/null) || {
      echo '{"error": "Request failed: network error or invalid URL"}' >&2
      return 1
    }
    http_code=$(echo "$body" | tail -1)
    body=$(echo "$body" | sed '$d')
  fi

  if [[ "$http_code" -ge 400 ]]; then
    echo "$body" >&2
    return 1
  fi

  echo "$body"
}

# POST request to Hermod API
# Usage: surf_post "/v1/onchain/query" '{"sql": "SELECT 1"}'
surf_post() {
  local path="$1"
  local data="${2:-{}}"
  local url="${HERMOD_URL}${path}"

  local http_code body
  body=$(curl -s --max-time 30 -w "\n%{http_code}" \
    -X POST \
    -H "Authorization: Bearer ${HERMOD_TOKEN}" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d "$data" \
    "$url" 2>/dev/null) || {
    echo '{"error": "Request failed: network error or invalid URL"}' >&2
    return 1
  }

  http_code=$(echo "$body" | tail -1)
  body=$(echo "$body" | sed '$d')

  # Auto-refresh on 401 and retry once
  if [[ "$http_code" == "401" ]] && _surf_try_refresh; then
    body=$(curl -s --max-time 30 -w "\n%{http_code}" \
      -X POST \
      -H "Authorization: Bearer ${HERMOD_TOKEN}" \
      -H "Content-Type: application/json" \
      -H "Accept: application/json" \
      -d "$data" \
      "$url" 2>/dev/null) || {
      echo '{"error": "Request failed: network error or invalid URL"}' >&2
      return 1
    }
    http_code=$(echo "$body" | tail -1)
    body=$(echo "$body" | sed '$d')
  fi

  if [[ "$http_code" -ge 400 ]]; then
    echo "$body" >&2
    return 1
  fi

  echo "$body"
}

# GET request to Hermod proxy route
# Usage: surf_proxy_get "coingecko" "/api/v3/simple/price" "ids=bitcoin&vs_currencies=usd"
surf_proxy_get() {
  local service="$1"
  local path="$2"
  local query="${3:-}"
  surf_get "/v1/proxy/${service}${path}" "$query"
}

# POST request to Hermod proxy route
# Usage: surf_proxy_post "recon" "/intel/addresses/batch" '{"addresses":["0x..."]}'
surf_proxy_post() {
  local service="$1"
  local path="$2"
  local data="${3:-{}}"
  surf_post "/v1/proxy/${service}${path}" "$data"
}

# URL-encode a string
# Usage: encoded=$(surf_urlencode "my query string")
surf_urlencode() {
  local string="$1"
  python3 -c "import urllib.parse; print(urllib.parse.quote('$string', safe=''))"
}
