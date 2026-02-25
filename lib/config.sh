#!/usr/bin/env bash
# config.sh — Configuration loader for surf-core CLI tools
# Loads HERMOD_URL and HERMOD_TOKEN from:
#   1. Environment variables (highest priority)
#   2. Session file at ~/.surf-core/session.json (persisted by surf-session)
# Auto-refreshes access token if it expires within 5 minutes.

set -euo pipefail

# Resolve lib directory regardless of where the script is called from (supports symlinks)
_resolve_path() { python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$1" 2>/dev/null || echo "$1"; }
SURF_CORE_LIB_DIR="$(cd "$(dirname "$(_resolve_path "${BASH_SOURCE[0]}")")" && pwd)"
SURF_CORE_ROOT="$(cd "$SURF_CORE_LIB_DIR/.." && pwd)"

SURF_SESSION_FILE="${HOME}/.surf-core/session.json"
: "${MUNINN_URL:=https://api.stg.ask.surf/muninn}"

# Read a field from session JSON
_surf_read_field() {
  python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get(sys.argv[2],''))" "$SURF_SESSION_FILE" "$1" 2>/dev/null || echo ""
}

# Auto-load from session file if env vars are not set
if [[ -z "${HERMOD_TOKEN:-}" && -f "$SURF_SESSION_FILE" ]]; then
  HERMOD_TOKEN=$(_surf_read_field "hermod_token")
  _SURF_SESSION_URL=$(_surf_read_field "hermod_url")
  if [[ -n "$_SURF_SESSION_URL" ]]; then
    : "${HERMOD_URL:=$_SURF_SESSION_URL}"
  fi
  unset _SURF_SESSION_URL
fi

: "${HERMOD_URL:=https://api.stg.ask.surf/gateway}"
: "${HERMOD_TOKEN:=}"

# Auto-refresh if token expires within 5 minutes and refresh_token is available
if [[ -n "$HERMOD_TOKEN" && -f "$SURF_SESSION_FILE" ]]; then
  _surf_exp=$(python3 -c "
import json, sys, base64
token = sys.argv[1]
payload = token.split('.')[1]
payload += '=' * (4 - len(payload) % 4)
d = json.loads(base64.urlsafe_b64decode(payload))
print(d.get('exp', 0))
" "$HERMOD_TOKEN" 2>/dev/null) || _surf_exp=0

  _surf_now=$(date +%s)
  if [[ "$_surf_exp" -gt 0 && $((_surf_exp - _surf_now)) -le 300 ]]; then
    _surf_refresh=$(_surf_read_field "refresh_token")
    if [[ -n "$_surf_refresh" ]]; then
      _surf_raw=$(curl -s --max-time 10 -X POST \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -d "{\"refresh_token\": \"$_surf_refresh\"}" \
        "${MUNINN_URL}/v2/auth/refresh" 2>/dev/null) || _surf_raw=""
      if [[ -n "$_surf_raw" ]]; then
        _surf_new_token=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('data',{}).get('access_token',''))" <<< "$_surf_raw" 2>/dev/null) || _surf_new_token=""
        if [[ -n "$_surf_new_token" ]]; then
          _surf_new_refresh=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('data',{}).get('refresh_token',''))" <<< "$_surf_raw" 2>/dev/null) || _surf_new_refresh=""
          : "${_surf_new_refresh:=$_surf_refresh}"
          HERMOD_TOKEN="$_surf_new_token"
          # Update session file
          python3 -c "
import json, sys
data = {'hermod_url': sys.argv[1], 'hermod_token': sys.argv[2], 'refresh_token': sys.argv[3]}
with open(sys.argv[4], 'w') as f:
    json.dump(data, f, indent=2)
" "$HERMOD_URL" "$_surf_new_token" "$_surf_new_refresh" "$SURF_SESSION_FILE" 2>/dev/null
          echo '{"auto_refresh": true, "message": "Access token refreshed automatically."}' >&2
        fi
      fi
    fi
  fi
  unset _surf_exp _surf_now _surf_refresh _surf_raw _surf_new_token _surf_new_refresh
fi

# Validate configuration
surf_check_setup() {
  local errors=0

  if [[ -z "$HERMOD_TOKEN" ]]; then
    echo '{"error": "No Hermod session. Run: surf-session login"}' >&2
    errors=1
  fi

  if [[ -z "$HERMOD_URL" ]]; then
    echo '{"error": "HERMOD_URL is not set."}' >&2
    errors=1
  fi

  if [[ $errors -gt 0 ]]; then
    return 1
  fi

  echo "{\"status\": \"ok\", \"hermod_url\": \"$HERMOD_URL\"}"
  return 0
}
