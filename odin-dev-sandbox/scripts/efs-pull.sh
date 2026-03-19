#!/usr/bin/env bash
# Pull EFS workspace files from urania-agent pod to local.
#
# Usage:
#   efs-pull.sh <user_id|session_id> [subcommand] [options]
#
# Subcommands:
#   tree     Show file tree (default)
#   pull     Download project to local
#   list     List all outputs/projects for a user
#   du       Show disk usage
#
# Options:
#   --session    Treat the ID as a session_id (resolve user from Datadog)
#   --project    Specific project timestamp (e.g. 20260313_160659)
#   --output     Local output directory (default: /tmp/efs-pull/<user_id>/)
#   --context    kubectl context (default: prd)
#   --code-only  Skip .claude/ dir, pull only workspace/outputs/

set -euo pipefail

# --- Defaults ---
KUBE_CONTEXT="prd"
NAMESPACE="app"
POD_SELECTOR="app=urania-agent"
EFS_BASE="/workspaces"
LOCAL_BASE="/tmp/efs-pull"
SUBCMD="tree"
USER_ID=""
SESSION_ID=""
PROJECT=""
CODE_ONLY=false
OUTPUT_DIR=""

# --- Colors ---
RED='\033[31m'
GREEN='\033[32m'
CYAN='\033[36m'
GRAY='\033[90m'
BOLD='\033[1m'
RESET='\033[0m'

log()  { printf "${GRAY}%s${RESET}\n" "$*" >&2; }
info() { printf "${GREEN}%s${RESET}\n" "$*" >&2; }
err()  { printf "${RED}ERROR: %s${RESET}\n" "$*" >&2; exit 1; }

# --- Arg parsing ---
parse_args() {
    [[ $# -lt 1 ]] && usage
    local positional=()

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --session)    SESSION_ID="$2"; shift 2 ;;
            --project)    PROJECT="$2"; shift 2 ;;
            --output)     OUTPUT_DIR="$2"; shift 2 ;;
            --context)    KUBE_CONTEXT="$2"; shift 2 ;;
            --code-only)  CODE_ONLY=true; shift ;;
            -h|--help)    usage ;;
            -*)           err "Unknown flag: $1" ;;
            *)            positional+=("$1"); shift ;;
        esac
    done

    # Parse positionals: <id> [subcommand]
    if [[ ${#positional[@]} -ge 1 ]]; then
        # First positional could be a subcommand or an ID
        case "${positional[0]}" in
            tree|pull|list|du) SUBCMD="${positional[0]}" ;;
            *) USER_ID="${positional[0]}" ;;
        esac
    fi
    if [[ ${#positional[@]} -ge 2 ]]; then
        case "${positional[1]}" in
            tree|pull|list|du) SUBCMD="${positional[1]}" ;;
            *) [[ -z "$USER_ID" ]] && USER_ID="${positional[1]}" ;;
        esac
    fi

    # If --session was given, session_id overrides
    if [[ -n "$SESSION_ID" ]]; then
        USER_ID=""
    fi
}

usage() {
    cat >&2 <<'EOF'
Usage: efs-pull.sh <user_id> [tree|pull|list|du] [options]
       efs-pull.sh --session <session_id> [tree|pull|list|du] [options]

Subcommands:
  tree          Show file tree of workspace (default)
  list          List all project outputs for the user
  pull          Download project to local
  du            Show disk usage breakdown

Options:
  --session ID  Resolve user_id from a session_id via workspace paths
  --project TS  Target a specific project (e.g. 20260313_160659)
  --output DIR  Local output directory (default: /tmp/efs-pull/<user_id>/)
  --context CTX kubectl context (default: prd)
  --code-only   Skip .claude/ metadata, only pull code from workspace/outputs/

Examples:
  efs-pull.sh 2430ede5-3fab-4e91-9fb5-243d4ee951e0 tree
  efs-pull.sh 2430ede5-3fab-4e91-9fb5-243d4ee951e0 list
  efs-pull.sh 2430ede5-3fab-4e91-9fb5-243d4ee951e0 pull --project 20260313_160659
  efs-pull.sh 2430ede5-3fab-4e91-9fb5-243d4ee951e0 pull --code-only
  efs-pull.sh --session 5b1e6162-2a04-457c-9624-8eea9d996411 tree
EOF
    exit 0
}

# --- Helpers ---
get_pod() {
    local pod
    pod=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods \
        -l "$POD_SELECTOR" --field-selector=status.phase=Running \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    [[ -z "$pod" ]] && err "No running urania-agent pod found (context=$KUBE_CONTEXT)"
    echo "$pod"
}

kexec() {
    # Filter out k8s websocket noise from stderr only
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD" -- "$@" 2> >(grep -v 'websocket\|Unknown stream' >&2 || true)
}

# Raw exec for binary output (tar), no stderr filtering
kexec_raw() {
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD" -- "$@" 2>/dev/null
}

resolve_session_to_user() {
    # Tiered resolution: Redis (hot) → Muninn DB (persistent) → Datadog (logs)
    # Each tier provides different data:
    #   Redis:  user_id + project_dir (active sessions only)
    #   DB:     user_id + mode        (permanent, but no project_dir)
    #   Datadog: user_id + project_dir (from parsed logs, ~15-30d retention)

    _try_redis && return 0
    _try_muninn_db && return 0
    _try_datadog && return 0
    err "Could not resolve session $SESSION_ID from any source (Redis/DB/Datadog)"
}

_try_redis() {
    log "[L1] Trying Redis..."
    local output
    output=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD" -- \
        python3 -c "
import os, redis, re, json
r = redis.from_url(os.environ['REDIS_URL'])
sid = '$SESSION_ID'
project_dir = r.get(f'vibe:project_dir:session:{sid}')
if not project_dir:
    print(json.dumps({'source': 'redis', 'found': False}))
else:
    project_dir = project_dir.decode()
    m_uid = re.search(r'/workspaces/([a-f0-9-]{36})/', project_dir)
    m_proj = re.search(r'/outputs/(\d{8}_\d{6})', project_dir)
    print(json.dumps({
        'source': 'redis', 'found': True,
        'user_id': m_uid.group(1) if m_uid else '',
        'project': m_proj.group(1) if m_proj else '',
    }))
" 2>/dev/null) || true
    _apply_result "$output"
}

_try_muninn_db() {
    log "[L2] Trying Muninn DB (via muninn API)..."
    # Query session via muninn's internal API (crypto_agent_session table)
    # muninn-api pod is Go binary (no python3), so use curl from urania pod
    local output
    output=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD" -- \
        python3 -c "
import json, urllib.request
try:
    # muninn internal k8s service endpoint
    url = 'http://muninn-api.app.svc.cluster.local:8080/muninn/api/v1/crypto-agent/sessions/$SESSION_ID'
    req = urllib.request.Request(url, headers={'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req, timeout=3)
    data = json.loads(resp.read())
    session = data.get('data', data)
    uid = session.get('user_id', '')
    if uid:
        print(json.dumps({'source': 'db', 'found': True, 'user_id': uid}))
    else:
        print(json.dumps({'source': 'db', 'found': False}))
except Exception as e:
    print(json.dumps({'source': 'db', 'found': False, 'error': str(e)[:100]}))
" 2>/dev/null) || true
    _apply_result "$output"
}

_try_datadog() {
    log "[L3] Trying Datadog logs..."
    local ddlog_script
    ddlog_script="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../../odin-dev-datadog/scripts 2>/dev/null && pwd)/ddlog.py"
    if [[ ! -f "$ddlog_script" ]]; then
        log "  Datadog skill not found, skipping"
        return 1
    fi

    # Must unset SOCKS proxy before calling Datadog API
    unset all_proxy ALL_PROXY 2>/dev/null || true

    local ddlog_dir
    ddlog_dir="$(dirname "$ddlog_script")"

    local dd_output
    dd_output=$(cd "$ddlog_dir/.." && uv run python "$ddlog_script" query \
        "@session_id:$SESSION_ID AND project_dir" \
        --time 15d -n 1 --json 2>/dev/null) || true

    if [[ -z "$dd_output" ]]; then
        log "  No Datadog logs found"
        return 1
    fi

    # Parse first valid JSON line from ddlog output and extract user_id + project
    local output
    output=$(echo "$dd_output" | python3 -c "
import json, sys, re
result = {'source': 'datadog', 'found': False}
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try:
        obj = json.loads(line)
        attrs = obj.get('attributes', {}).get('attributes', {})
        msg = obj.get('attributes', {}).get('message', '')
        uid = attrs.get('user_id', '')
        if not uid:
            m = re.search(r'/workspaces/([a-f0-9-]{36})/', msg)
            if m: uid = m.group(1)
        if uid:
            result = {'source': 'datadog', 'found': True, 'user_id': uid, 'project': ''}
            m = re.search(r'/outputs/(\d{8}_\d{6})', msg)
            if m: result['project'] = m.group(1)
            break
    except: pass
print(json.dumps(result))
" 2>/dev/null) || true
    _apply_result "$output"
}

_apply_result() {
    local output="$1"
    [[ -z "$output" ]] && return 1

    local found source resolved_uid resolved_project
    found=$(echo "$output" | python3 -c "import json,sys; print(json.load(sys.stdin).get('found',False))" 2>/dev/null) || true
    [[ "$found" != "True" ]] && return 1

    source=$(echo "$output" | python3 -c "import json,sys; print(json.load(sys.stdin).get('source',''))" 2>/dev/null) || true
    resolved_uid=$(echo "$output" | python3 -c "import json,sys; print(json.load(sys.stdin).get('user_id',''))" 2>/dev/null) || true
    resolved_project=$(echo "$output" | python3 -c "import json,sys; print(json.load(sys.stdin).get('project',''))" 2>/dev/null) || true

    if [[ -z "$resolved_uid" ]]; then
        return 1
    fi

    USER_ID="$resolved_uid"
    info "Resolved via $source → user $USER_ID"

    if [[ -z "$PROJECT" && -n "$resolved_project" ]]; then
        PROJECT="$resolved_project"
        info "Auto-detected project: $PROJECT"
    fi
    return 0
}

# --- Subcommands ---
cmd_tree() {
    local target="$EFS_BASE/$USER_ID"
    if [[ -n "$PROJECT" ]]; then
        target="$EFS_BASE/$USER_ID/workspace/outputs/$PROJECT"
    fi

    log "File tree: $target (pod=$POD)"
    printf "${CYAN}${BOLD}%s${RESET}\n" "$target"

    # Use find -printf to get type info in one call (avoids per-file kexec roundtrips)
    kexec find "$target" -maxdepth 4 \
        -not -path '*/node_modules/*' \
        -not -path '*/.git/*' \
        -not -path '*/.vite/*' \
        -not -path '*/dist/*' \
        -printf '%y %P\n' 2>/dev/null \
        | sort -t' ' -k2 \
        | while IFS=' ' read -r ftype relpath; do
            [[ -z "$relpath" ]] && continue
            local depth
            depth=$(printf '%s' "$relpath" | tr -cd '/' | wc -c)
            local indent=""
            for ((i=0; i<depth; i++)); do indent="$indent  "; done
            local name
            name=$(basename "$relpath")
            if [[ "$ftype" == "d" ]]; then
                printf "%s${CYAN}%s/${RESET}\n" "$indent" "$name"
            else
                printf "%s%s\n" "$indent" "$name"
            fi
        done
}

cmd_list() {
    local outputs_dir="$EFS_BASE/$USER_ID/workspace/outputs"
    log "Projects for user $USER_ID (pod=$POD)"

    printf "${BOLD}%-20s %10s %s${RESET}\n" "PROJECT" "SIZE" "FILES"
    printf "%-20s %10s %s\n" "-------" "----" "-----"

    kexec ls -1 "$outputs_dir" 2>/dev/null | while IFS= read -r proj; do
        local size files
        size=$(kexec du -sh "$outputs_dir/$proj" 2>/dev/null | awk '{print $1}')
        files=$(kexec find "$outputs_dir/$proj" -type f -not -path '*/node_modules/*' -not -path '*/.git/*' 2>/dev/null | wc -l)
        printf "%-20s %10s %s files\n" "$proj" "$size" "$files"
    done
}

cmd_du() {
    local target="$EFS_BASE/$USER_ID"
    log "Disk usage for $target (pod=$POD)"
    kexec du -sh "$target" 2>/dev/null
    kexec du -sh "$target"/*/ 2>/dev/null | sort -rh
    echo ""
    if kexec test -d "$target/workspace/outputs" 2>/dev/null; then
        log "Per-project breakdown:"
        kexec du -sh "$target/workspace/outputs"/*/ 2>/dev/null | sort -rh
    fi
}

cmd_pull() {
    local remote_path="$EFS_BASE/$USER_ID"
    local tar_excludes="--exclude=node_modules --exclude=.git --exclude=.vite --exclude=dist --exclude=.cache"

    # Determine what to pull
    local tar_path
    if [[ -n "$PROJECT" ]]; then
        tar_path="workspace/outputs/$PROJECT"
        log "Pulling project: $PROJECT"
    elif [[ "$CODE_ONLY" == true ]]; then
        tar_path="workspace/outputs"
        log "Pulling all projects (code only)"
    else
        tar_path="."
        log "Pulling entire workspace"
    fi

    # Set output dir
    [[ -z "$OUTPUT_DIR" ]] && OUTPUT_DIR="$LOCAL_BASE/$USER_ID"
    mkdir -p "$OUTPUT_DIR"

    # Tar on pod → stream → extract locally
    local tar_file="$OUTPUT_DIR/workspace.tar.gz"
    log "Packing on pod $POD..."
    # tar may exit non-zero due to symlink/permission warnings — tolerate it if output file exists
    kexec_raw tar czf - -C "$remote_path" $tar_excludes "$tar_path" > "$tar_file" || true
    [[ ! -s "$tar_file" ]] && err "Failed to download workspace (empty tar)"

    local size
    size=$(du -sh "$tar_file" | awk '{print $1}')
    info "Downloaded: $tar_file ($size)"

    # Extract
    log "Extracting..."
    tar xzf "$tar_file" -C "$OUTPUT_DIR"
    rm "$tar_file"

    # Summary
    local file_count
    file_count=$(find "$OUTPUT_DIR" -type f | wc -l | tr -d ' ')
    info "Extracted to: $OUTPUT_DIR ($file_count files)"

    # Show tree
    printf "\n${BOLD}Local file tree:${RESET}\n"
    find "$OUTPUT_DIR" -maxdepth 3 -not -path '*/node_modules/*' | head -30
    local total
    total=$(find "$OUTPUT_DIR" -maxdepth 3 -not -path '*/node_modules/*' | wc -l)
    if [[ "$total" -gt 30 ]]; then
        printf "${GRAY}  ... and %d more entries${RESET}\n" $((total - 30))
    fi
}

# --- Main ---
parse_args "$@"

# Resolve session → user if needed
POD=$(get_pod)

if [[ -n "$SESSION_ID" && -z "$USER_ID" ]]; then
    resolve_session_to_user
fi

[[ -z "$USER_ID" ]] && err "No user_id provided. Use <user_id> or --session <session_id>"

# Verify workspace exists (use raw exec — kexec grep filter breaks exit code for test)
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD" -- test -d "$EFS_BASE/$USER_ID" 2>/dev/null \
    || err "Workspace not found: $EFS_BASE/$USER_ID"

case "$SUBCMD" in
    tree) cmd_tree ;;
    list) cmd_list ;;
    du)   cmd_du ;;
    pull) cmd_pull ;;
    *)    err "Unknown subcommand: $SUBCMD" ;;
esac
