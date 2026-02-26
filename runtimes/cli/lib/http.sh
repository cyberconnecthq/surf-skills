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
