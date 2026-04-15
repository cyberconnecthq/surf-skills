#!/bin/bash
# update-check.sh — Check for and apply Surf skill updates.
#
# Compares the local SKILL.md metadata.version against the latest
# version in the GitHub repo. If a newer version exists, downloads
# the updated SKILL.md automatically.
#
# Usage: bash update-check.sh
#
# Exit codes:
#   0 — up to date or updated successfully
#   1 — error (printed to stderr, non-fatal)

set -euo pipefail

REPO="asksurf-ai/surf-skills"
SKILL_PATH="skills/surf/SKILL.md"
RAW_URL="https://raw.githubusercontent.com/$REPO/main/$SKILL_PATH"

# Find the local SKILL.md — check common install locations.
LOCAL=""
for candidate in \
    "${BASH_SOURCE[0]%/scripts/*}/SKILL.md" \
    "$HOME/.claude/skills/surf/SKILL.md" \
    ; do
    if [ -f "$candidate" ]; then
        LOCAL="$candidate"
        break
    fi
done

if [ -z "$LOCAL" ]; then
    echo "surf skill: cannot find local SKILL.md" >&2
    exit 0
fi

# Extract local version from frontmatter metadata.version.
local_version=$(grep -A1 'metadata:' "$LOCAL" 2>/dev/null | grep 'version:' | head -1 | sed 's/.*version:[[:space:]]*"\{0,1\}\([^"]*\)"\{0,1\}/\1/' || true)
if [ -z "$local_version" ]; then
    echo "surf skill: no metadata.version in local SKILL.md" >&2
    exit 0
fi

# Fetch remote SKILL.md version (just the frontmatter, not the whole file).
remote_version=$(curl -sfL --max-time 3 "$RAW_URL" 2>/dev/null | grep -A1 'metadata:' | grep 'version:' | head -1 | sed 's/.*version:[[:space:]]*"\{0,1\}\([^"]*\)"\{0,1\}/\1/' || true)
if [ -z "$remote_version" ]; then
    # Network error or parse failure — skip silently.
    exit 0
fi

if [ "$local_version" = "$remote_version" ]; then
    echo "surf skill v$local_version — up to date."
    exit 0
fi

# New version available — download and replace.
echo "surf skill: updating v$local_version → v$remote_version..."
if curl -sfL --max-time 10 "$RAW_URL" -o "$LOCAL.tmp" 2>/dev/null; then
    mv "$LOCAL.tmp" "$LOCAL"
    echo "surf skill updated to v$remote_version."
else
    rm -f "$LOCAL.tmp"
    echo "surf skill: update failed, continuing with v$local_version" >&2
fi
