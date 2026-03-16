#!/usr/bin/env bash
# Collect vibe session data from Langfuse, Datadog, and EFS.
# Outputs a structured directory with all raw data for analysis.
#
# Usage:
#   collect.sh --session <session_id>
#   collect.sh --user <user_id>
#   collect.sh --email <email>
#
# Output: /tmp/vibe-analysis/<session_id>/
#   ├── meta.json           # Resolved session metadata
#   ├── datadog/             # Datadog logs (timeline, errors, perf)
#   ├── langfuse/            # Langfuse traces (if found)
#   ├── efs/                 # Project files from EFS
#   └── summary.md           # Auto-generated summary

set -euo pipefail

# --- Paths ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
DDLOG="$SKILLS_DIR/odin-dev-datadog/scripts/ddlog.py"
DDLOG_DIR="$SKILLS_DIR/odin-dev-datadog"
LANGFUSE="$SKILLS_DIR/odin-data-langfuse-trace/fetch_trace.py"
LANGFUSE_DIR="$SKILLS_DIR/odin-data-langfuse-trace"
EFS_PULL="$SKILLS_DIR/odin-dev-sandbox/scripts/efs-pull.sh"
OUTPUT_BASE="/tmp/vibe-analysis"

# --- Colors ---
RED='\033[31m'; GREEN='\033[32m'; CYAN='\033[36m'; GRAY='\033[90m'
BOLD='\033[1m'; RESET='\033[0m'
log()  { printf "${GRAY}%s${RESET}\n" "$*" >&2; }
info() { printf "${GREEN}%s${RESET}\n" "$*" >&2; }
err()  { printf "${RED}ERROR: %s${RESET}\n" "$*" >&2; exit 1; }
section() { printf "\n${BOLD}${CYAN}━━━ %s ━━━${RESET}\n" "$*" >&2; }

# --- Args ---
SESSION_ID="" USER_ID="" EMAIL="" TIME_RANGE="7d"

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --session) SESSION_ID="$2"; shift 2 ;;
            --user)    USER_ID="$2"; shift 2 ;;
            --email)   EMAIL="$2"; shift 2 ;;
            --time)    TIME_RANGE="$2"; shift 2 ;;
            -h|--help) usage ;;
            *)         # Bare arg — guess type
                       if [[ "$1" =~ ^[a-f0-9-]{36}$ ]]; then
                           SESSION_ID="$1"
                       elif [[ "$1" =~ @ ]]; then
                           EMAIL="$1"
                       else
                           SESSION_ID="$1"
                       fi
                       shift ;;
        esac
    done
    if [[ -z "$SESSION_ID" && -z "$USER_ID" && -z "$EMAIL" ]]; then
        usage
    fi
}

usage() {
    cat >&2 <<'EOF'
Usage: collect.sh <session_id>
       collect.sh --session <session_id>
       collect.sh --user <user_id>
       collect.sh --email <email>
       collect.sh --time 15d <session_id>    # extend search window

Collects data from Langfuse, Datadog, and EFS into /tmp/vibe-analysis/<session_id>/
EOF
    exit 0
}

# --- Input Resolution ---
resolve_email_to_user() {
    section "Resolving email: $EMAIL"
    # Try Datadog first (faster than DB query)
    unset all_proxy ALL_PROXY 2>/dev/null || true
    local dd_result
    dd_result=$(cd "$DDLOG_DIR" && uv run python "$DDLOG" query \
        "\"$EMAIL\"" --time 30d -n 1 --json 2>/dev/null) || true

    if [[ -n "$dd_result" ]]; then
        USER_ID=$(echo "$dd_result" | python3 -c "
import json, sys
for line in sys.stdin:
    try:
        obj = json.loads(line.strip())
        uid = obj.get('attributes',{}).get('attributes',{}).get('user_id','')
        if uid:
            print(uid)
            sys.exit(0)
    except: pass
" 2>/dev/null) || true
    fi

    if [[ -n "$USER_ID" ]]; then
        info "Email $EMAIL → user $USER_ID (via Datadog)"
    else
        err "Could not resolve email $EMAIL. Try using --user or --session directly."
    fi
}

resolve_user_to_session() {
    section "Finding latest session for user: $USER_ID"
    unset all_proxy ALL_PROXY 2>/dev/null || true
    local dd_result
    dd_result=$(cd "$DDLOG_DIR" && uv run python "$DDLOG" query \
        "@user_id:$USER_ID AND \"New session\"" \
        --time "$TIME_RANGE" -n 1 --sort desc --json 2>/dev/null) || true

    if [[ -n "$dd_result" ]]; then
        SESSION_ID=$(echo "$dd_result" | python3 -c "
import json, sys, re
for line in sys.stdin:
    try:
        obj = json.loads(line.strip())
        sid = obj.get('attributes',{}).get('attributes',{}).get('session_id','')
        if not sid:
            msg = obj.get('attributes',{}).get('message','')
            m = re.search(r'session=([a-f0-9-]{36})', msg)
            if m: sid = m.group(1)
        if sid:
            print(sid)
            sys.exit(0)
    except: pass
" 2>/dev/null) || true
    fi

    if [[ -n "$SESSION_ID" ]]; then
        info "Latest session: $SESSION_ID"
    else
        err "No sessions found for user $USER_ID in the last $TIME_RANGE"
    fi
}

# --- Data Collection ---
collect_datadog() {
    section "Collecting Datadog logs"
    local dd_dir="$OUT_DIR/datadog"
    mkdir -p "$dd_dir"
    unset all_proxy ALL_PROXY 2>/dev/null || true

    # Timeline (full log stream)
    log "  Fetching full timeline..."
    (cd "$DDLOG_DIR" && uv run python "$DDLOG" session "$SESSION_ID" \
        --time "$TIME_RANGE" --sort asc -n 500 2>/dev/null) \
        > "$dd_dir/timeline.txt" 2>&1 || true

    # Errors and warnings
    log "  Fetching warnings/errors..."
    (cd "$DDLOG_DIR" && uv run python "$DDLOG" session "$SESSION_ID" \
        --time "$TIME_RANGE" --level warn -n 100 --verbose 2>/dev/null) \
        > "$dd_dir/errors.txt" 2>&1 || true

    # Performance metrics
    log "  Fetching performance data..."
    (cd "$DDLOG_DIR" && uv run python "$DDLOG" query \
        "@session_id:$SESSION_ID AND (STARTUP_PERF OR DATA_API_PERF OR LLM)" \
        --time "$TIME_RANGE" -n 100 2>/dev/null) \
        > "$dd_dir/performance.txt" 2>&1 || true

    # Stats summary (JSON for programmatic use)
    (cd "$DDLOG_DIR" && uv run python "$DDLOG" session "$SESSION_ID" \
        --time "$TIME_RANGE" --stats-only 2>/dev/null) \
        > "$dd_dir/stats.txt" 2>&1 || true

    # Extract key metadata from first few logs
    (cd "$DDLOG_DIR" && uv run python "$DDLOG" session "$SESSION_ID" \
        --time "$TIME_RANGE" -n 5 --json --sort asc 2>/dev/null) \
        > "$dd_dir/first_events.json" 2>&1 || true

    local line_count
    line_count=$(wc -l < "$dd_dir/timeline.txt" 2>/dev/null | tr -d ' ')
    info "  Datadog: $line_count log lines collected"
}

collect_langfuse() {
    section "Collecting Langfuse traces"
    local lf_dir="$OUT_DIR/langfuse"
    mkdir -p "$lf_dir"

    # Find Langfuse trace_id from Datadog logs
    unset all_proxy ALL_PROXY 2>/dev/null || true
    local trace_ids
    trace_ids=$(cd "$DDLOG_DIR" && uv run python "$DDLOG" query \
        "@session_id:$SESSION_ID AND LangfuseTracer" \
        --time "$TIME_RANGE" -n 5 --json 2>/dev/null \
        | python3 -c "
import json, sys, re
seen = set()
for line in sys.stdin:
    try:
        obj = json.loads(line.strip())
        msg = obj.get('attributes',{}).get('message','')
        # Look for trace_id in log message
        m = re.search(r'trace_id=([a-f0-9-]{32,36})', msg)
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            print(m.group(1))
    except: pass
" 2>/dev/null) || true

    if [[ -z "$trace_ids" ]]; then
        # Fallback: try session_id as Langfuse session_id directly
        log "  No trace_id in Datadog, trying session_id as Langfuse session..."
        (cd "$LANGFUSE_DIR" && uv run "$LANGFUSE" --session "$SESSION_ID" --fast 2>/dev/null) \
            > "$lf_dir/fetch.log" 2>&1 || true

        if grep -q "Found .* traces" "$lf_dir/fetch.log" 2>/dev/null; then
            local lf_session_dir
            lf_session_dir=$(grep "Session data saved to:" "$lf_dir/fetch.log" | awk '{print $NF}')
            if [[ -n "$lf_session_dir" && -d "$lf_session_dir" ]]; then
                cp -r "$lf_session_dir"/* "$lf_dir/" 2>/dev/null || true
                info "  Langfuse: session traces collected"
                return
            fi
        fi
        log "  No Langfuse traces found for this session"
        echo "No Langfuse traces found for session $SESSION_ID" > "$lf_dir/not_found.txt"
        return
    fi

    # Fetch each trace
    local count=0
    for tid in $trace_ids; do
        log "  Fetching trace: ${tid:0:16}..."
        (cd "$LANGFUSE_DIR" && uv run "$LANGFUSE" "$tid" --fast 2>/dev/null) \
            >> "$lf_dir/fetch.log" 2>&1 || true
        count=$((count + 1))
    done

    # Copy trace data to our output dir
    for tid in $trace_ids; do
        local trace_dir="/tmp/trace_analysis/${tid:0:16}"
        if [[ -d "$trace_dir" ]]; then
            cp -r "$trace_dir" "$lf_dir/trace_${tid:0:12}" 2>/dev/null || true
        fi
    done

    info "  Langfuse: $count traces collected"
}

collect_efs() {
    section "Collecting EFS files"
    local efs_dir="$OUT_DIR/efs"
    mkdir -p "$efs_dir"

    # Tree view
    log "  Getting file tree..."
    bash "$EFS_PULL" --session "$SESSION_ID" tree \
        > "$efs_dir/tree.txt" 2>&1 || true

    # Pull project files
    log "  Pulling project files..."
    bash "$EFS_PULL" --session "$SESSION_ID" pull --code-only \
        --output "$efs_dir/project" \
        > "$efs_dir/pull.log" 2>&1 || true

    local file_count
    file_count=$(find "$efs_dir/project" -type f 2>/dev/null | wc -l | tr -d ' ')
    info "  EFS: $file_count files pulled"
}

# --- Summary Generation ---
generate_summary() {
    section "Generating summary"
    local summary="$OUT_DIR/summary.md"

    # Extract metadata from Datadog first events
    local user_id_short model mode start_time services
    if [[ -f "$OUT_DIR/datadog/first_events.json" ]]; then
        read -r user_id_short model mode start_time services < <(python3 -c "
import json, sys, re
uid = model = mode = start = ''
services = set()
with open('$OUT_DIR/datadog/first_events.json') as f:
    for line in f:
        try:
            obj = json.loads(line.strip())
            attrs = obj.get('attributes',{})
            inner = attrs.get('attributes',{})
            if not uid: uid = inner.get('user_id','')
            if not start: start = str(attrs.get('timestamp',''))[:19]
            services.add(attrs.get('service',''))
            msg = attrs.get('message','')
            m = re.search(r'model=([^\s,)]+)', msg)
            if m and not model: model = m.group(1)
            m = re.search(r'mode=(\w+)', msg)
            if m and not mode: mode = m.group(1)
        except: pass
print(f'{uid[:12] if uid else \"unknown\"} {model or \"unknown\"} {mode or \"vibe\"} {start or \"unknown\"} {\",\".join(sorted(services - {\"\"}))}')
" 2>/dev/null) || true
    fi

    # Count errors from Datadog
    local error_count warn_count
    error_count=$(grep -c 'ERROR' "$OUT_DIR/datadog/errors.txt" 2>/dev/null || echo "0")
    warn_count=$(grep -c 'WARN' "$OUT_DIR/datadog/errors.txt" 2>/dev/null || echo "0")

    # Count EFS files
    local efs_files
    efs_files=$(find "$OUT_DIR/efs/project" -type f 2>/dev/null | wc -l | tr -d ' ')

    # Check Langfuse availability
    local lf_status="not found"
    if [[ -f "$OUT_DIR/langfuse/not_found.txt" ]]; then
        lf_status="no traces"
    elif ls "$OUT_DIR/langfuse/trace_"* >/dev/null 2>&1; then
        lf_status="$(ls -d "$OUT_DIR/langfuse/trace_"* 2>/dev/null | wc -l | tr -d ' ') traces"
    fi

    cat > "$summary" <<EOF
# Vibe Session Analysis: ${SESSION_ID:0:12}...

## Summary
| Field | Value |
|-------|-------|
| Session | \`$SESSION_ID\` |
| User | \`${user_id_short:-unknown}\` |
| Model | \`${model:-unknown}\` |
| Mode | ${mode:-vibe} |
| Start | ${start_time:-unknown} |
| Services | ${services:-unknown} |
| Errors | $error_count errors, $warn_count warnings |
| Code Output | $efs_files files |
| Langfuse | $lf_status |

## Data Collected

### Datadog (Service Telemetry)
- \`datadog/timeline.txt\` — Full session log stream
- \`datadog/errors.txt\` — Warnings and errors with details
- \`datadog/performance.txt\` — Startup, LLM, and API performance metrics
- \`datadog/stats.txt\` — Aggregate statistics

### Langfuse (Agent Reasoning)
$(if [[ "$lf_status" == "no traces" ]]; then
    echo "- No Langfuse traces found for this session"
    echo "- Langfuse session_id may differ from vibe session_id"
else
    echo "- Trace data in \`langfuse/\` subdirectories"
    echo "- Key files: \`call_tree.txt\`, \`tools_only.txt\`, \`llm_only.txt\`, \`cost_summary.txt\`"
fi)

### EFS (Code Output)
- \`efs/tree.txt\` — Remote file structure
- \`efs/project/\` — Downloaded project files ($efs_files files)

## Next Steps
Read the files above and analyze:
1. **Agent reasoning**: What did the agent decide? Were tool calls appropriate?
2. **Service health**: Any errors or latency issues in the startup/execution flow?
3. **Code quality**: Does the generated code structure make sense? Any issues?
4. **Cross-dimensional**: Did infra problems cause agent failures or code gaps?
EOF

    info "Summary: $summary"
}

# --- Main ---
parse_args "$@"

# Resolve input to session_id
if [[ -n "$EMAIL" && -z "$USER_ID" ]]; then
    resolve_email_to_user
fi

if [[ -n "$USER_ID" && -z "$SESSION_ID" ]]; then
    resolve_user_to_session
fi

if [[ -z "$SESSION_ID" ]]; then
    err "Could not determine session_id"
fi

# Setup output dir
OUT_DIR="$OUTPUT_BASE/$SESSION_ID"
mkdir -p "$OUT_DIR"

section "Analyzing session: $SESSION_ID"
log "Output: $OUT_DIR"

# Save meta
cat > "$OUT_DIR/meta.json" <<EOF
{"session_id": "$SESSION_ID", "user_id": "$USER_ID", "email": "$EMAIL", "collected_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
EOF

# Collect from all sources
collect_datadog
collect_langfuse
collect_efs

# Generate summary
generate_summary

section "Collection complete"
info "All data saved to: $OUT_DIR"
echo ""
printf "${BOLD}Files:${RESET}\n"
find "$OUT_DIR" -maxdepth 2 -type f | sort | while read -r f; do
    size=$(du -sh "$f" 2>/dev/null | awk '{print $1}')
    printf "  %-60s %s\n" "${f#"$OUT_DIR"/}" "$size"
done
echo ""
printf "${BOLD}To analyze, read:${RESET}\n"
printf "  ${CYAN}$OUT_DIR/summary.md${RESET}\n"
