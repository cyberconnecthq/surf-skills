#!/usr/bin/env bash
set -euo pipefail

# surf-core installer
# Sets up restish API config, skills, and CLI tools.
#
# Usage:
#   ./install.sh            Install everything
#   ./install.sh --remove   Uninstall everything
#   ./install.sh --check    Verify installation status
#   ./install.sh --help     Show help

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$HOME/.claude/skills"
BIN_DIR="$HOME/.surf-core/bin"
SURF_SESSION_FILE="${HOME}/.surf-core/session.json"
PATH_LINE='export PATH="$HOME/.surf-core/bin:$PATH"'
PATH_COMMENT="# surf-core CLI tools"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
DIM='\033[2m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_shell_rcs() {
  local rcs=()
  if [ "$(uname)" = "Darwin" ] || [ -n "${ZSH_VERSION:-}" ]; then
    rcs+=("$HOME/.zshenv")
  fi
  [ -f "$HOME/.bashrc" ] && rcs+=("$HOME/.bashrc")
  [ -f "$HOME/.bash_profile" ] && rcs+=("$HOME/.bash_profile")
  if [ ${#rcs[@]} -eq 0 ]; then
    rcs+=("$HOME/.bashrc")
  fi
  echo "${rcs[@]}"
}

_restish_config_dir() {
  case "$(uname)" in
    Darwin) echo "$HOME/Library/Application Support/restish" ;;
    *)      echo "${XDG_CONFIG_HOME:-$HOME/.config}/restish" ;;
  esac
}

_hermod_url_from_session() {
  if [[ -f "$SURF_SESSION_FILE" ]]; then
    python3 -c "
import json, sys
data = json.load(open(sys.argv[1]))
print(data.get('hermod_url', ''))
" "$SURF_SESSION_FILE" 2>/dev/null || echo ""
  else
    echo ""
  fi
}

# ---------------------------------------------------------------------------
# Install steps
# ---------------------------------------------------------------------------

check_restish() {
  if command -v restish &>/dev/null; then
    echo -e "  ${GREEN}found${NC} restish ($(command -v restish))"
    return 0
  fi
  echo -e "  ${RED}restish not found${NC}"
  echo ""
  echo "  Install restish first:"
  echo "    macOS:  brew install restish"
  echo "    Linux:  go install github.com/danielgtaylor/restish@latest"
  echo "    Other:  https://rest.sh/#/guide?id=installation"
  echo ""
  exit 1
}

install_restish_config() {
  local config_dir
  config_dir=$(_restish_config_dir)
  local apis_json="$config_dir/apis.json"
  local template="$SCRIPT_DIR/config/apis.json.template"

  # Determine hermod URL
  local hermod_url
  hermod_url=$(_hermod_url_from_session)
  : "${hermod_url:=https://api.stg.ask.surf}"

  # Absolute path to surf-auth
  local surf_auth_path="$SCRIPT_DIR/bin/surf-auth"

  mkdir -p "$config_dir"

  if [[ -f "$apis_json" ]]; then
    # Merge: inject/update "surf" key without clobbering other APIs
    python3 -c "
import json, sys

apis_path = sys.argv[1]
template_path = sys.argv[2]
hermod_url = sys.argv[3]
auth_path = sys.argv[4]

with open(apis_path) as f:
    apis = json.load(f)

with open(template_path) as f:
    tmpl_text = f.read()

tmpl_text = tmpl_text.replace('__HERMOD_URL__', hermod_url)
tmpl_text = tmpl_text.replace('__SURF_AUTH_PATH__', auth_path)
tmpl = json.loads(tmpl_text)

apis['surf'] = tmpl['surf']

with open(apis_path, 'w') as f:
    json.dump(apis, f, indent=2)
    f.write('\n')
" "$apis_json" "$template" "$hermod_url" "$surf_auth_path"
    echo -e "  ${GREEN}merged${NC} 'surf' key into $apis_json"
  else
    # Fresh install: write from template
    python3 -c "
import sys

template_path = sys.argv[1]
output_path = sys.argv[2]
hermod_url = sys.argv[3]
auth_path = sys.argv[4]

with open(template_path) as f:
    content = f.read()

content = content.replace('__HERMOD_URL__', hermod_url)
content = content.replace('__SURF_AUTH_PATH__', auth_path)

with open(output_path, 'w') as f:
    f.write(content)
" "$template" "$apis_json" "$hermod_url" "$surf_auth_path"
    echo -e "  ${GREEN}created${NC} $apis_json"
  fi
}

install_skills() {
  mkdir -p "$SKILL_DIR"
  local count=0

  # surf-api skill
  local surf_api_src="$SCRIPT_DIR/skills/surf-api"
  local surf_api_dst="$SKILL_DIR/surf-api"
  if [[ -d "$surf_api_src" ]]; then
    if [[ -L "$surf_api_dst" ]]; then
      local existing
      existing=$(readlink "$surf_api_dst")
      if [[ "$existing" == "$surf_api_src" ]]; then
        echo -e "  ${DIM}surf-api already linked${NC}"
      else
        rm "$surf_api_dst"
        ln -s "$surf_api_src" "$surf_api_dst"
        echo -e "  ${GREEN}+${NC} surf-api"
        ((count++))
      fi
    elif [[ -e "$surf_api_dst" ]]; then
      echo -e "  ${YELLOW}skip${NC} surf-api (non-symlink exists)"
    else
      ln -s "$surf_api_src" "$surf_api_dst"
      echo -e "  ${GREEN}+${NC} surf-api"
      ((count++))
    fi
  fi

  # surf-login skill
  local surf_login_src="$SCRIPT_DIR/login"
  local surf_login_dst="$SKILL_DIR/surf-login"
  if [[ -d "$surf_login_src" ]]; then
    if [[ -L "$surf_login_dst" ]]; then
      local existing
      existing=$(readlink "$surf_login_dst")
      if [[ "$existing" == "$surf_login_src" ]]; then
        echo -e "  ${DIM}surf-login already linked${NC}"
      else
        rm "$surf_login_dst"
        ln -s "$surf_login_src" "$surf_login_dst"
        echo -e "  ${GREEN}+${NC} surf-login"
        ((count++))
      fi
    elif [[ -e "$surf_login_dst" ]]; then
      echo -e "  ${YELLOW}skip${NC} surf-login (non-symlink exists)"
    else
      ln -s "$surf_login_src" "$surf_login_dst"
      echo -e "  ${GREEN}+${NC} surf-login"
      ((count++))
    fi
  fi

  [[ $count -eq 0 ]] && echo -e "  ${DIM}all skills up to date${NC}"
}

install_bin() {
  mkdir -p "$BIN_DIR"

  # Symlink surf-session
  local src="$SCRIPT_DIR/login/scripts/surf-session"
  local dst="$BIN_DIR/surf-session"
  if [[ -L "$dst" ]]; then
    local existing
    existing=$(readlink "$dst")
    if [[ "$existing" != "$src" ]]; then
      rm "$dst"
      ln -s "$src" "$dst"
      echo -e "  ${GREEN}+${NC} surf-session"
    else
      echo -e "  ${DIM}surf-session already linked${NC}"
    fi
  elif [[ -e "$dst" ]]; then
    echo -e "  ${YELLOW}skip${NC} surf-session (non-symlink exists)"
  else
    ln -s "$src" "$dst"
    echo -e "  ${GREEN}+${NC} surf-session"
  fi

  # PATH setup
  if echo "$PATH" | tr ':' '\n' | grep -qx "$BIN_DIR"; then
    echo -e "  ${DIM}PATH already configured${NC}"
  else
    local added_to=""
    for rc in $(_shell_rcs); do
      if ! grep -qF 'surf-core/bin' "$rc" 2>/dev/null; then
        echo "" >> "$rc"
        echo "$PATH_COMMENT" >> "$rc"
        echo "$PATH_LINE" >> "$rc"
        added_to="$added_to $(basename "$rc")"
      fi
    done
    if [[ -n "$added_to" ]]; then
      echo -e "  ${GREEN}added${NC} PATH to$added_to"
      echo -e "  ${YELLOW}->  Run: source ~/.zshrc${NC} (or restart terminal)"
    else
      echo -e "  ${DIM}PATH already in shell rc${NC}"
    fi
    export PATH="$BIN_DIR:$PATH"
  fi
}

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

cmd_install() {
  echo "Installing surf-core..."
  echo ""

  echo -e "${CYAN}[1/4]${NC} Checking restish"
  check_restish

  echo -e "${CYAN}[2/4]${NC} Restish API config"
  install_restish_config

  echo -e "${CYAN}[3/4]${NC} Skills -> $SKILL_DIR/"
  install_skills

  echo -e "${CYAN}[4/4]${NC} CLI tools -> $BIN_DIR/"
  install_bin

  echo ""
  echo -e "${GREEN}Done.${NC} Try: restish surf list-operations"
}

cmd_remove() {
  echo "Removing surf-core..."
  echo ""

  local removed=0

  # Remove skill symlinks
  for name in surf-api surf-login; do
    local target="$SKILL_DIR/$name"
    if [[ -L "$target" ]] && [[ "$(readlink "$target")" == *"surf-core"* ]]; then
      rm "$target"
      echo -e "  ${RED}-${NC} skill: $name"
      ((removed++))
    fi
  done

  # Remove bin symlinks
  if [[ -d "$BIN_DIR" ]]; then
    for f in "$BIN_DIR"/surf-*; do
      [[ -L "$f" ]] || continue
      echo -e "  ${RED}-${NC} bin: $(basename "$f")"
      rm "$f"
      ((removed++))
    done
    rmdir "$BIN_DIR" 2>/dev/null || true
  fi

  # Remove restish surf config
  local config_dir
  config_dir=$(_restish_config_dir)
  local apis_json="$config_dir/apis.json"
  if [[ -f "$apis_json" ]]; then
    python3 -c "
import json, sys
path = sys.argv[1]
with open(path) as f:
    data = json.load(f)
if 'surf' in data:
    del data['surf']
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
    print('removed', file=sys.stderr)
" "$apis_json" 2>/dev/null && {
      echo -e "  ${RED}-${NC} restish: surf API config"
      ((removed++))
    }
  fi

  # Remove PATH from shell rcs
  for rc in $(_shell_rcs); do
    if grep -qF 'surf-core/bin' "$rc" 2>/dev/null; then
      sed -i.bak '/# surf-core CLI tools/d' "$rc"
      sed -i.bak '/surf-core\/bin/d' "$rc"
      rm -f "${rc}.bak"
      echo -e "  ${RED}-${NC} PATH from $(basename "$rc")"
      ((removed++))
    fi
  done

  echo ""
  echo "Removed $removed items. Session file (~/.surf-core/session.json) kept."
}

cmd_check() {
  echo "surf-core installation status:"
  echo ""

  # restish
  if command -v restish &>/dev/null; then
    echo -e "  restish:     ${GREEN}installed${NC}"
  else
    echo -e "  restish:     ${RED}not found${NC}"
  fi

  # restish config
  local config_dir
  config_dir=$(_restish_config_dir)
  local apis_json="$config_dir/apis.json"
  if [[ -f "$apis_json" ]] && python3 -c "import json; json.load(open('$apis_json'))['surf']" 2>/dev/null; then
    echo -e "  API config:  ${GREEN}configured${NC}"
  else
    echo -e "  API config:  ${RED}missing${NC}"
  fi

  # Skills
  for name in surf-api surf-login; do
    local target="$SKILL_DIR/$name"
    if [[ -L "$target" ]] && [[ -e "$target" ]]; then
      echo -e "  skill/$name: ${GREEN}linked${NC}"
    else
      echo -e "  skill/$name: ${RED}missing${NC}"
    fi
  done

  # bin
  if [[ -L "$BIN_DIR/surf-session" ]] && [[ -e "$BIN_DIR/surf-session" ]]; then
    echo -e "  surf-session: ${GREEN}linked${NC}"
  else
    echo -e "  surf-session: ${RED}missing${NC}"
  fi

  # PATH
  if echo "$PATH" | tr ':' '\n' | grep -qx "$BIN_DIR"; then
    echo -e "  PATH:        ${GREEN}configured${NC}"
  else
    echo -e "  PATH:        ${YELLOW}not in current shell${NC} (run: source ~/.zshrc)"
  fi

  # Session
  if [[ -f "$SURF_SESSION_FILE" ]]; then
    echo -e "  session:     ${GREEN}exists${NC}"
  else
    echo -e "  session:     ${YELLOW}not found${NC} (run: surf-session login)"
  fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

case "${1:---install}" in
  --remove|--uninstall) cmd_remove ;;
  --check|--status)     cmd_check ;;
  --help|-h)
    echo "Usage: ./install.sh [--install|--remove|--check|--help]"
    echo ""
    echo "  --install   Install restish config + skills + CLI tools (default)"
    echo "  --remove    Uninstall everything"
    echo "  --check     Verify installation status"
    echo "  --help      Show this help"
    ;;
  --install|*)          cmd_install ;;
esac
