#!/bin/bash
# update-check.sh — Check for and apply Surf skill updates.
#
# Compares the local SKILL.md metadata.version against the latest
# GitHub release tag. If a newer version exists, downloads the
# updated SKILL.md and scripts from that release.
#
# Usage: bash update-check.sh
#
# Exit codes:
#   0 — up to date or updated successfully
#   1 — error (printed to stderr, non-fatal)

set -euo pipefail

REPO="asksurf-ai/surf-skills"
SKILL_PATH="skills/surf/SKILL.md"

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

SKILL_DIR="$(dirname "$LOCAL")"

# Extract local version from frontmatter metadata.version.
local_version=$(grep -A1 'metadata:' "$LOCAL" 2>/dev/null | grep 'version:' | head -1 | sed 's/.*version:[[:space:]]*"\{0,1\}\([^"]*\)"\{0,1\}/\1/' || true)
if [ -z "$local_version" ]; then
    echo "surf skill: no metadata.version in local SKILL.md" >&2
    exit 0
fi

# Fetch latest release tag from GitHub API.
# Extract tag_name and strip leading "v" if present.
release_tag=$(curl -sfL --max-time 3 "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null | grep '"tag_name"' | head -1 | sed 's/.*"tag_name":[[:space:]]*"\([^"]*\)".*/\1/' || true)
remote_version="${release_tag#v}"
if [ -z "$remote_version" ]; then
    # Network error or no releases — skip silently.
    exit 0
fi

if [ "$local_version" = "$remote_version" ]; then
    echo "surf skill v$local_version — up to date."
    exit 0
fi

# New version available — download from release tag.
echo "surf skill: updating v$local_version → v$remote_version..."
TAG="$release_tag"
RAW_URL="https://raw.githubusercontent.com/$REPO/$TAG"

# Update SKILL.md
if curl -sfL --max-time 10 "$RAW_URL/$SKILL_PATH" -o "$LOCAL.tmp" 2>/dev/null; then
    mv "$LOCAL.tmp" "$LOCAL"
else
    rm -f "$LOCAL.tmp"
    echo "surf skill: failed to download SKILL.md" >&2
    exit 0
fi

# Update scripts
mkdir -p "$SKILL_DIR/scripts"
curl -sfL --max-time 10 "$RAW_URL/skills/surf/scripts/update-check.sh" -o "$SKILL_DIR/scripts/update-check.sh.tmp" 2>/dev/null && \
    mv "$SKILL_DIR/scripts/update-check.sh.tmp" "$SKILL_DIR/scripts/update-check.sh" && \
    chmod +x "$SKILL_DIR/scripts/update-check.sh" || true

echo "surf skill updated to v$remote_version."
