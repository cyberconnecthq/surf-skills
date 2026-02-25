#!/usr/bin/env bash
# config.sh — Configuration loader for surf-core CLI tools
# Loads HERMOD_URL and HERMOD_TOKEN from:
#   1. Environment variables (highest priority)
#   2. Session file at ~/.surf-core/session.json (persisted by surf-session configure)

set -euo pipefail

# Resolve lib directory regardless of where the script is called from
SURF_CORE_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SURF_CORE_ROOT="$(cd "$SURF_CORE_LIB_DIR/.." && pwd)"

SURF_SESSION_FILE="${HOME}/.surf-core/session.json"

# Auto-load from session file if env vars are not set
if [[ -z "${HERMOD_TOKEN:-}" && -f "$SURF_SESSION_FILE" ]]; then
  HERMOD_TOKEN=$(python3 -c "import json; print(json.load(open('$SURF_SESSION_FILE')).get('hermod_token',''))" 2>/dev/null) || HERMOD_TOKEN=""
  _SURF_SESSION_URL=$(python3 -c "import json; print(json.load(open('$SURF_SESSION_FILE')).get('hermod_url',''))" 2>/dev/null) || _SURF_SESSION_URL=""
  if [[ -n "$_SURF_SESSION_URL" ]]; then
    : "${HERMOD_URL:=$_SURF_SESSION_URL}"
  fi
  unset _SURF_SESSION_URL
fi

: "${HERMOD_URL:=https://api.asksurf.ai/gateway}"
: "${HERMOD_TOKEN:=}"

# Validate configuration
surf_check_setup() {
  local errors=0

  if [[ -z "$HERMOD_TOKEN" ]]; then
    echo '{"error": "No Hermod session. Run: surf-session configure --token <JWT>"}' >&2
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
