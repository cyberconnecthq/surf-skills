#!/usr/bin/env bash
# build-skills.sh — Assemble final SKILL.md from knowledge/ + runtimes/
#
# Source layout:
#   knowledge/{skill}/*.md          — platform-agnostic API knowledge
#   runtimes/{runtime}/{skill}/
#     SKILL.md                      — template with {{VAR}} placeholders
#     build.conf                    — INCLUDE, STRIP_SECTIONS, template vars
#
# Output:
#   dist/{runtime}/{skill}/SKILL.md — assembled, agent-ready
#
# Usage:
#   ./scripts/build-skills.sh                          # build all
#   ./scripts/build-skills.sh http trading-data         # build one
#   ENV=odin ./scripts/build-skills.sh http trading-data  # with env override

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

build_skill() {
  local runtime="$1" skill="$2"
  local runtime_dir="runtimes/${runtime}/${skill}"
  local runtime_md="${runtime_dir}/SKILL.md"
  local knowledge_dir="knowledge/${skill}"
  local out_dir="dist/${runtime}/${skill}"

  # Allow env-specific override: runtimes/http/trading-data/build.odin.conf
  local env_name="${ENV:-}"
  local build_conf="${runtime_dir}/build.conf"
  if [[ -n "$env_name" && -f "${runtime_dir}/build.${env_name}.conf" ]]; then
    build_conf="${runtime_dir}/build.${env_name}.conf"
  fi

  if [[ ! -f "$runtime_md" ]]; then
    echo "SKIP: ${runtime}/${skill}" >&2
    return
  fi

  # --- Parse build.conf ---
  local include_files="endpoints.md responses.md patterns.md"
  local strip_sections=""
  local var_keys="" var_vals=""

  if [[ -f "$build_conf" ]]; then
    while IFS= read -r line; do
      [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
      local key="${line%%=*}" val="${line#*=}"
      case "$key" in
        INCLUDE) include_files="$val" ;;
        STRIP_SECTIONS) strip_sections="$val" ;;
        *) var_keys="${var_keys}${key}"$'\n'; var_vals="${var_vals}${val}"$'\n' ;;
      esac
    done < "$build_conf"
  fi

  # --- Assemble ---
  mkdir -p "$out_dir"

  local assembled=""

  # 1. Runtime header (up to "## Knowledge" marker)
  assembled="$(sed '/^## Knowledge/,$d' "$runtime_md")"

  # 2. Inline knowledge files
  if [[ -d "$knowledge_dir" ]]; then
    assembled+=$'\n---\n'
    for f in $include_files; do
      [[ -f "${knowledge_dir}/${f}" ]] && assembled+=$'\n'"$(cat "${knowledge_dir}/${f}")"$'\n'
    done
  fi

  # 3. Template variable substitution: {{VAR}} → value
  if [[ -n "$var_keys" ]]; then
    local IFS_BAK="$IFS"
    IFS=$'\n'
    local keys_arr=($var_keys) vals_arr=($var_vals)
    IFS="$IFS_BAK"
    for i in "${!keys_arr[@]}"; do
      local k="${keys_arr[$i]}" v="${vals_arr[$i]}"
      [[ -n "$k" ]] && assembled="${assembled//\{\{${k}\}\}/${v}}"
    done
  fi

  # 4. Strip sections
  if [[ -n "$strip_sections" ]]; then
    assembled="$(echo "$assembled" | python3 -c "
import sys, re
content = sys.stdin.read()
section = sys.argv[1]
content = re.sub(r'^## ' + re.escape(section) + r'.*?(?=^## |\Z)', '', content, flags=re.MULTILINE | re.DOTALL)
sys.stdout.write(content)
" "$strip_sections")"
  fi

  echo "$assembled" > "${out_dir}/SKILL.md"

  # 5. Copy extra assets (scripts/, references/, lib/) if present
  for asset in scripts references lib; do
    if [[ -d "${runtime_dir}/${asset}" ]]; then
      cp -a "${runtime_dir}/${asset}" "${out_dir}/"
    fi
  done

  echo "OK  dist/${runtime}/${skill}/  (SKILL.md $(wc -l < "${out_dir}/SKILL.md" | tr -d ' ')L)"
}

# --- Main ---
if [[ $# -eq 2 ]]; then
  build_skill "$1" "$2"
  exit 0
fi

for rd in runtimes/*/; do
  runtime="$(basename "$rd")"
  for sd in "${rd}"*/; do
    [[ -d "$sd" ]] || continue
    build_skill "$runtime" "$(basename "$sd")"
  done
done
echo "Done."
