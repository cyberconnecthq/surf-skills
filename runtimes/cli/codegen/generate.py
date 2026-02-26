#!/usr/bin/env python3
"""
surf-core CLI code generator — reads Hermod Swagger 2.0 spec and generates
bash CLI scripts, SKILL.md, and endpoints.md for each data domain.

Usage:
    python3 runtimes/cli/codegen/generate.py \
        --spec ../hermod/docs/hermod/Hermod_swagger.json \
        --output-dir runtimes/cli/ \
        --knowledge-dir knowledge/ \
        [--domains token,market,social]  \
        [--dry-run]
"""

import argparse
import json
import os
import re
import sys
import textwrap
from collections import defaultdict
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Tags we generate for (lowercase). Matches Swagger tags.
DOMAIN_TAGS = {
    "market", "token", "project", "wallet", "social", "news", "web", "onchain",
}

# Credit cost per domain (standard endpoints).  Proxy endpoints get higher cost.
DOMAIN_CREDITS = {
    "market": 1,
    "token": 1,
    "project": 1,
    "wallet": 1,
    "social": 1,
    "news": 1,
    "web": 1,
    "onchain": 5,
}

# Domains that should be skipped entirely for CLI generation
SKIP_TAGS = {"admin", "credit"}

# Example values for common param names — used in SKILL.md examples
EXAMPLE_VALUES = {
    "q": "bitcoin",
    "ids": "bitcoin,ethereum",
    "id": "ethereum",
    "project_id": "bitcoin",
    "symbol": "BTC",
    "address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "chain": "eth",
    "hash": "0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060",
    "handle": "vitalikbuterin",
    "asset": "btc",
    "metric": "volume",
    "name": "rsi",
    "vs_currencies": "usd",
    "vs_currency": "usd",
    "limit": "20",
    "offset": "0",
    "days": "30",
    "interval": "1d",
    "exchange": "binance",
    "window": "day",
    "status": "upcoming",
    "type": "general",
    "timeframe": "7d",
    "market_id": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    "sort": "desc",
    "site": "coindesk.com",
    "start": "2024-01-01",
    "end": "2024-12-31",
    "url": "https://ethereum.org",
}

# Map API param name -> CLI flag name (user-friendly aliases)
PARAM_FLAG_OVERRIDES = {
    "q": "--query",
}

# When the API param is "q", we still need to send "q" in the query string,
# but accept "--query" as the CLI flag.


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_swagger(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def tag_to_domain(tag: str) -> str:
    """Normalize swagger tag to domain key."""
    return tag.strip().lower()


def path_to_subcommand(path: str, domain: str) -> str:
    """Convert Swagger path to CLI subcommand name.

    /v1/market/price          -> price
    /v1/market/price/{id}/metrics -> price-metrics
    /v1/project/smart-followers/events -> smart-followers-events
    /v1/project/discover/fdv  -> discover-fdv
    /v1/social/user/{handle}  -> user
    /v1/social/user/{handle}/posts -> user-posts
    """
    prefix = f"/v1/{domain}/"
    if not path.startswith(prefix):
        return None

    rest = path[len(prefix):]
    # Remove path params like {handle}, {id}, {market_id}
    parts = rest.split("/")
    clean = []
    for p in parts:
        if p.startswith("{") and p.endswith("}"):
            continue
        if p:
            clean.append(p)
    if not clean:
        return None
    return "-".join(clean)


def param_to_flag(param_name: str) -> str:
    """Convert param name to --flag-name, respecting overrides."""
    if param_name in PARAM_FLAG_OVERRIDES:
        return PARAM_FLAG_OVERRIDES[param_name]
    return "--" + param_name.replace("_", "-")


def flag_to_var(flag: str) -> str:
    """Convert --flag-name to local_flag_name variable."""
    return "local_" + flag.lstrip("-").replace("-", "_")


def is_proxy_path(path: str) -> bool:
    return "/proxy/" in path


def is_raw_onchain(path: str) -> bool:
    return path.startswith("/v1/raw-onchain/")


def extract_enum_values(param: dict) -> list:
    """Extract enum values from a parameter."""
    return param.get("enum", [])


def extract_default(param: dict) -> str | None:
    """Extract default value from a parameter."""
    d = param.get("default")
    if d is not None:
        return str(d)
    return None


def credit_for_endpoint(domain: str, path: str) -> int:
    """Determine credit cost for an endpoint."""
    if is_proxy_path(path):
        return 2  # default proxy cost
    return DOMAIN_CREDITS.get(domain, 1)


def _strip_quotes(s: str) -> str:
    """Strip single and double quotes from a string for safe bash embedding."""
    return s.replace("'", "").replace('"', "")


def build_description_hint(param: dict) -> str:
    """Extract a useful hint from the param description for error messages."""
    desc = param.get("description", "")
    # Try to extract example from description
    m = re.search(r"\(e\.g\.?\s*['\"]?([^)\"']+)", desc)
    if m:
        result = m.group(1).strip().rstrip(")").strip(",").strip()
        return _strip_quotes(result)
    return ""


def build_error_hint(param: dict) -> str:
    """Build a comprehensive error hint for missing required param errors.

    Returns a string like:
      (e.g. 0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48)
    or for enum params:
      . Valid: exchange_flow, etf_flow, exchange_reserve

    All returned text is sanitized for safe embedding in bash single-quoted strings.
    """
    if param["enum"]:
        return ". Valid: " + ", ".join(param["enum"])
    desc = param.get("description", "")
    hint = param.get("hint", "")
    if hint:
        return f" (e.g. {_strip_quotes(hint)})"

    # Try to extract "Valid values: ..." or "Available: ..." from description
    m = re.search(r"[Vv]alid\s*(values)?[:\s]+(.+?)(?:\.|$)", desc)
    if m:
        return ". Valid: " + _strip_quotes(m.group(2).strip())

    m = re.search(r"[Aa]vailable[:\s]+(.+?)(?:\.|$)", desc)
    if m:
        return ". Valid: " + _strip_quotes(m.group(1).strip())

    # Try to extract "Supported: ..." from description
    m = re.search(r"[Ss]upported[:\s]+(.+?)(?:\.|$)", desc)
    if m:
        return ". Valid: " + _strip_quotes(m.group(1).strip())

    # Try to extract metric list like "metric: value1, value2, value3"
    m = re.search(r":\s+([\w_]+(?:,\s*[\w_]+)+)\s*$", desc)
    if m:
        return ". Valid: " + _strip_quotes(m.group(1).strip())

    # Try to extract content in parentheses as hint
    m = re.search(r"\(([^)]+)\)", desc)
    if m:
        inner = m.group(1).strip()
        if len(inner) < 120:
            return f" ({_strip_quotes(inner)})"

    return ""


def safe_json_string(s: str) -> str:
    """Escape a string for embedding in JSON."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


# ---------------------------------------------------------------------------
# Endpoint data model
# ---------------------------------------------------------------------------

class Endpoint:
    def __init__(self, path: str, method: str, op: dict, domain: str):
        self.path = path
        self.method = method.upper()
        self.op = op
        self.domain = domain
        self.summary = op.get("summary", "")
        self.description = op.get("description", "")
        self.subcommand = path_to_subcommand(path, domain)
        self.params = self._parse_params()
        self.credit = credit_for_endpoint(domain, path)
        self.is_post = method.upper() == "POST"
        self.has_body = any(p["in"] == "body" for p in op.get("parameters", []))

    def _parse_params(self):
        params = []
        for p in self.op.get("parameters", []):
            if p.get("in") == "body":
                continue  # handled separately
            params.append({
                "name": p["name"],
                "flag": param_to_flag(p["name"]),
                "var": flag_to_var(param_to_flag(p["name"])),
                "required": p.get("required", False),
                "type": p.get("type", "string"),
                "description": p.get("description", ""),
                "default": extract_default(p),
                "enum": extract_enum_values(p),
                "in": p.get("in", "query"),
                "hint": build_description_hint(p),
            })
        return params

    @property
    def query_params(self):
        return [p for p in self.params if p["in"] == "query"]

    @property
    def path_params(self):
        return [p for p in self.params if p["in"] == "path"]

    @property
    def required_params(self):
        return [p for p in self.params if p["required"]]

    @property
    def optional_params(self):
        return [p for p in self.params if not p["required"]]


# ---------------------------------------------------------------------------
# Group endpoints by domain
# ---------------------------------------------------------------------------

def group_endpoints(spec: dict, domain_filter: set | None = None) -> dict[str, list[Endpoint]]:
    groups = defaultdict(list)
    base_path = spec.get("basePath", "")

    for path, methods in spec.get("paths", {}).items():
        for method, op in methods.items():
            if method.lower() not in ("get", "post", "put", "delete", "patch"):
                continue

            tags = [tag_to_domain(t) for t in op.get("tags", [])]
            for tag in tags:
                if tag in SKIP_TAGS:
                    continue
                if tag not in DOMAIN_TAGS:
                    continue
                if domain_filter and tag not in domain_filter:
                    continue
                if is_proxy_path(path):
                    continue  # skip proxy routes
                if is_raw_onchain(path):
                    continue  # skip raw-onchain duplicates

                ep = Endpoint(path, method, op, tag)
                if ep.subcommand:
                    groups[tag].append(ep)

    # Sort each group by subcommand name
    for tag in groups:
        groups[tag].sort(key=lambda e: e.subcommand)

    return dict(groups)


# ---------------------------------------------------------------------------
# Bash script generator
# ---------------------------------------------------------------------------

def generate_bash_script(domain: str, endpoints: list[Endpoint]) -> str:
    """Generate a complete bash CLI script for a domain."""
    cmd_name = f"surf-{domain}"
    api_prefix = f"/v1/{domain}"

    all_cmds = ", ".join(e.subcommand for e in endpoints)

    lines = []
    lines.append('#!/usr/bin/env bash')
    lines.append(f'# {cmd_name} — CLI for {domain} data via Hermod API')
    lines.append(f'# Usage: {cmd_name} <subcommand> [flags]')
    lines.append('')
    lines.append('set -euo pipefail')
    lines.append('')
    lines.append('# Resolve symlinks so ../../lib/ works even when installed via `npx skills add`')
    lines.append('_resolve_path() { python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$1" 2>/dev/null || echo "$1"; }')
    lines.append('SCRIPT_DIR="$(cd "$(dirname "$(_resolve_path "${BASH_SOURCE[0]}")")" && pwd)"')
    lines.append('source "$SCRIPT_DIR/../../lib/config.sh"')
    lines.append('source "$SCRIPT_DIR/../../lib/http.sh"')
    lines.append('')
    lines.append(f'API_PREFIX="{api_prefix}"')
    lines.append('')
    lines.append(f'ALL_COMMANDS="{all_cmds}"')
    lines.append('')

    # Generate usage()
    lines.append('usage() {')
    lines.append("  cat <<'EOF'")
    lines.append('{"usage": {')
    lines.append(f'  "command": "{cmd_name}",')
    lines.append('  "subcommands": {')

    usage_entries = []
    for ep in endpoints:
        args_parts = []
        for p in ep.required_params:
            example = _example_for_param(p)
            args_parts.append(f'{p["flag"]} {example}')
        for p in ep.optional_params:
            default = p["default"]
            example = _example_for_param(p)
            if default:
                args_parts.append(f'[{p["flag"]} {default}]')
            else:
                args_parts.append(f'[{p["flag"]} {example}]')

        args_str = " ".join(args_parts)
        credit_str = f'{ep.credit} credit{"s" if ep.credit > 1 else ""}'
        desc_str = f'{ep.summary} ({credit_str})'
        desc_str = safe_json_string(desc_str)
        args_str = safe_json_string(args_str)
        usage_entries.append(f'    "{ep.subcommand}": {{"args": "{args_str}", "description": "{desc_str}"}}')

    usage_entries.append(f'    "--check-setup": {{"args": "", "description": "Verify environment configuration"}}')
    lines.append(",\n".join(usage_entries))
    lines.append('  }')
    lines.append('}}')
    lines.append('EOF')
    lines.append('}')
    lines.append('')

    # Generate dispatch
    lines.append('# Main dispatch')
    lines.append('case "${1:---help}" in')
    lines.append('  --check-setup) surf_check_setup ;;')
    lines.append('  --help|-h) usage ;;')
    lines.append('')

    for ep in endpoints:
        lines.extend(_generate_case_block(ep, domain))
        lines.append('')

    lines.append(f'  *) echo "{{\\\"error\\\": \\\"Unknown command: $1. Available: ${{ALL_COMMANDS}}\\\"}}" >&2; exit 1 ;;')
    lines.append('esac')

    return "\n".join(lines) + "\n"


def _example_for_param(p: dict) -> str:
    """Get a good example value for a parameter."""
    if p["enum"]:
        return p["enum"][0]
    name = p["name"]
    if name in EXAMPLE_VALUES:
        return EXAMPLE_VALUES[name]
    if "address" in name.lower():
        return "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    if "limit" in name.lower():
        return "20"
    if "offset" in name.lower():
        return "0"
    return "VALUE"


def _generate_case_block(ep: Endpoint, domain: str) -> list[str]:
    """Generate a case block for one endpoint."""
    lines = []
    lines.append(f'  {ep.subcommand})')
    lines.append('    shift')

    all_flags = [p["flag"] for p in ep.params]

    if ep.is_post and ep.has_body:
        # POST with body — special handling
        lines.extend(_generate_post_body_block(ep, all_flags))
    else:
        # GET (or POST without body params — treat query params)
        lines.extend(_generate_get_block(ep, all_flags, domain))

    lines.append('    ;;')
    return lines


def _generate_get_block(ep: Endpoint, all_flags: list[str], domain: str) -> list[str]:
    """Generate the body of a GET endpoint case block."""
    lines = []

    # Declare variables
    var_inits = []
    for p in ep.params:
        default = p["default"] or ""
        var_inits.append(f'{p["var"]}="{default}"')
    if var_inits:
        lines.append(f'    {" ".join(var_inits)}')

    # Flag parsing loop
    if ep.params:
        lines.append('    while [[ $# -gt 0 ]]; do')
        lines.append('      case "$1" in')
        for p in ep.params:
            lines.append(f'        {p["flag"]}) {p["var"]}="$2"; shift 2 ;;')
        flag_list = ", ".join(all_flags)
        lines.append(f'        *) echo "{{\\\"error\\\": \\\"Unknown flag: $1. Valid: {flag_list}\\\"}}" >&2; exit 1 ;;')
        lines.append('      esac')
        lines.append('    done')

    # Required param validation
    for p in ep.required_params:
        error_hint = build_error_hint(p)
        lines.append(f'    if [[ -z "${p["var"]}" ]]; then')
        lines.append(f'      echo \'{{"error": "{p["flag"]} is required{error_hint}"}}\' >&2; exit 1')
        lines.append('    fi')

    # Enum validation for all params that have enum values
    for p in ep.params:
        if p["enum"]:
            enum_str = ", ".join(p["enum"])
            var = p["var"]
            # Only validate if non-empty (required params already checked above)
            checks = " && ".join(f'[[ "${var}" != "{v}" ]]' for v in p["enum"])
            lines.append(f'    if [[ -n "${var}" ]] && {checks}; then')
            lines.append(f'      echo \'{{"error": "{p["flag"]} invalid. Valid: {enum_str}"}}\' >&2; exit 1')
            lines.append('    fi')

    # Build URL query string
    lines.extend(_build_query_string(ep, domain))

    return lines


def _build_query_string(ep: Endpoint, domain: str) -> list[str]:
    """Build the query string and issue surf_get/surf_post."""
    lines = []
    path_params = ep.path_params
    query_params = ep.query_params

    # Build the API path (handle path params)
    api_path = ep.path
    # Replace base /gateway if present from swagger basePath
    if api_path.startswith("/v1/"):
        path_expr = '"${API_PREFIX}/' + api_path[len(f"/v1/{ep.domain}/"):] + '"'
    else:
        path_expr = f'"{api_path}"'

    # Replace {param} with variable references in path
    for pp in path_params:
        placeholder = "{" + pp["name"] + "}"
        # For string params use urlencode
        path_expr = path_expr.replace(placeholder, f'$(surf_urlencode "${pp["var"]}")')

    # Build query string
    if query_params:
        required_qs = [p for p in query_params if p["required"]]
        optional_qs = [p for p in query_params if not p["required"]]

        if required_qs:
            first = required_qs[0]
            if first["type"] == "string":
                lines.append(f'    local_qs="{first["name"]}=$(surf_urlencode "${first["var"]}")"')
            else:
                lines.append(f'    local_qs="{first["name"]}=${first["var"]}"')
            for p in required_qs[1:]:
                if p["type"] == "string":
                    lines.append(f'    local_qs="${{local_qs}}&{p["name"]}=$(surf_urlencode "${p["var"]}")"')
                else:
                    lines.append(f'    local_qs="${{local_qs}}&{p["name"]}=${p["var"]}"')
        else:
            lines.append('    local_qs=""')

        for p in optional_qs:
            if p["default"]:
                # Always append since it has a default (var is always set)
                lines.append(f'    [[ -n "${p["var"]}" ]] && local_qs="${{local_qs:+${{local_qs}}&}}{p["name"]}=${p["var"]}"')
            else:
                lines.append(f'    [[ -n "${p["var"]}" ]] && local_qs="${{local_qs:+${{local_qs}}&}}{p["name"]}=${p["var"]}"')

        if ep.is_post:
            lines.append(f'    surf_post {path_expr} "${{local_qs}}"')
        else:
            lines.append(f'    surf_get {path_expr} "$local_qs"')
    elif path_params:
        if ep.is_post:
            lines.append(f'    surf_post {path_expr}')
        else:
            lines.append(f'    surf_get {path_expr}')
    else:
        if ep.is_post:
            lines.append(f'    surf_post {path_expr}')
        else:
            lines.append(f'    surf_get {path_expr}')

    return lines


def _generate_post_body_block(ep: Endpoint, all_flags: list[str]) -> list[str]:
    """Generate a POST-with-JSON-body case block.

    For POST endpoints with a body, we look at the description to determine
    what JSON to send and generate a simpler approach.
    """
    lines = []

    # For onchain endpoints with SQL body
    if ep.domain == "onchain" and "sql" in ep.subcommand:
        lines.append('    local_sql=""')
        lines.append('    while [[ $# -gt 0 ]]; do')
        lines.append('      case "$1" in')
        lines.append('        --sql) local_sql="$2"; shift 2 ;;')
        lines.append('        *) echo \'{"error": "Unknown flag: $1. Valid: --sql"}\' >&2; exit 1 ;;')
        lines.append('      esac')
        lines.append('    done')
        lines.append('    if [[ -z "$local_sql" ]]; then')
        lines.append('      echo \'{"error": "--sql is required (SQL query string)"}\' >&2; exit 1')
        lines.append('    fi')
        api_path = ep.path[len(f"/v1/{ep.domain}/"):]
        lines.append(f'    surf_post "${{API_PREFIX}}/{api_path}" "{{\\"sql\\": \\"$local_sql\\"}}"')
        return lines

    if ep.domain == "onchain" and ep.subcommand == "query":
        lines.append('    local_body=""')
        lines.append('    while [[ $# -gt 0 ]]; do')
        lines.append('      case "$1" in')
        lines.append('        --body) local_body="$2"; shift 2 ;;')
        lines.append('        *) echo \'{"error": "Unknown flag: $1. Valid: --body"}\' >&2; exit 1 ;;')
        lines.append('      esac')
        lines.append('    done')
        lines.append('    if [[ -z "$local_body" ]]; then')
        lines.append('      echo \'{"error": "--body is required (JSON structured query)"}\' >&2; exit 1')
        lines.append('    fi')
        api_path = ep.path[len(f"/v1/{ep.domain}/"):]
        lines.append(f'    surf_post "${{API_PREFIX}}/{api_path}" "$local_body"')
        return lines

    # For web/fetch
    if ep.domain == "web" and ep.subcommand == "fetch":
        lines.append('    local_url="" local_target="" local_remove=""')
        lines.append('    while [[ $# -gt 0 ]]; do')
        lines.append('      case "$1" in')
        lines.append('        --url) local_url="$2"; shift 2 ;;')
        lines.append('        --target-selector) local_target="$2"; shift 2 ;;')
        lines.append('        --remove-selector) local_remove="$2"; shift 2 ;;')
        lines.append('        *) echo \'{"error": "Unknown flag: $1. Valid: --url, --target-selector, --remove-selector"}\' >&2; exit 1 ;;')
        lines.append('      esac')
        lines.append('    done')
        lines.append('    if [[ -z "$local_url" ]]; then')
        lines.append('      echo \'{"error": "--url is required (e.g. https://ethereum.org)"}\' >&2; exit 1')
        lines.append('    fi')
        lines.append('    local_json="{\\"url\\": \\"$local_url\\""')
        lines.append('    [[ -n "$local_target" ]] && local_json="$local_json, \\"target_selector\\": \\"$local_target\\""')
        lines.append('    [[ -n "$local_remove" ]] && local_json="$local_json, \\"remove_selector\\": \\"$local_remove\\""')
        lines.append('    local_json="$local_json}"')
        lines.append('    surf_post "${API_PREFIX}/fetch" "$local_json"')
        return lines

    # For social/tweets POST
    if ep.domain == "social" and ep.subcommand == "tweets":
        lines.append('    local_ids=""')
        lines.append('    while [[ $# -gt 0 ]]; do')
        lines.append('      case "$1" in')
        lines.append('        --ids) local_ids="$2"; shift 2 ;;')
        lines.append('        *) echo \'{"error": "Unknown flag: $1. Valid: --ids"}\' >&2; exit 1 ;;')
        lines.append('      esac')
        lines.append('    done')
        lines.append('    if [[ -z "$local_ids" ]]; then')
        lines.append('      echo \'{"error": "--ids is required (JSON array of tweet IDs, max 100)"}\' >&2; exit 1')
        lines.append('    fi')
        lines.append('    surf_post "${API_PREFIX}/tweets" "{\\"tweet_ids\\": $local_ids}"')
        return lines

    # For wallet/labels/batch POST
    if ep.domain == "wallet" and ep.subcommand == "labels-batch":
        lines.append('    local_addresses=""')
        lines.append('    while [[ $# -gt 0 ]]; do')
        lines.append('      case "$1" in')
        lines.append('        --addresses) local_addresses="$2"; shift 2 ;;')
        lines.append('        *) echo \'{"error": "Unknown flag: $1. Valid: --addresses"}\' >&2; exit 1 ;;')
        lines.append('      esac')
        lines.append('    done')
        lines.append('    if [[ -z "$local_addresses" ]]; then')
        lines.append('      echo \'{"error": "--addresses is required (JSON array of hex addresses)"}\' >&2; exit 1')
        lines.append('    fi')
        lines.append('    surf_post "${API_PREFIX}/labels/batch" "{\\"addresses\\": $local_addresses}"')
        return lines

    # Generic POST fallback — accept --body as raw JSON
    lines.append('    local_body=""')
    lines.append('    while [[ $# -gt 0 ]]; do')
    lines.append('      case "$1" in')
    lines.append('        --body) local_body="$2"; shift 2 ;;')
    lines.append('        *) echo \'{"error": "Unknown flag: $1. Valid: --body"}\' >&2; exit 1 ;;')
    lines.append('      esac')
    lines.append('    done')
    lines.append('    if [[ -z "$local_body" ]]; then')
    lines.append('      echo \'{"error": "--body is required (JSON request body)"}\' >&2; exit 1')
    lines.append('    fi')
    api_path = ep.path[len(f"/v1/{ep.domain}/"):]
    lines.append(f'    surf_post "${{API_PREFIX}}/{api_path}" "$local_body"')
    return lines


# ---------------------------------------------------------------------------
# SKILL.md generator
# ---------------------------------------------------------------------------

def generate_skill_md(domain: str, endpoints: list[Endpoint]) -> str:
    """Generate SKILL.md for a domain."""
    cmd_name = f"surf-{domain}"
    script_path = f"runtimes/cli/{domain}/scripts/{cmd_name}"

    lines = []
    lines.append("---")
    lines.append(f"name: {cmd_name}")
    lines.append(f"description: {_domain_description(domain, endpoints)}")
    lines.append('tools: ["bash"]')
    lines.append("---")
    lines.append("")
    lines.append(f"# {domain.title()} Data — {_domain_title(domain)}")
    lines.append("")
    lines.append(f"Access {domain} data via the Hermod API Gateway. Standardized endpoints provide unified access to {domain} data.")
    lines.append("")
    lines.append("## When to Use")
    lines.append("")
    lines.append("Use this skill when you need to:")
    for ep in endpoints:
        lines.append(f"- {ep.summary}")
    lines.append("")
    lines.append("## CLI Usage")
    lines.append("")
    lines.append("```bash")
    lines.append("# Check setup")
    lines.append(f"{script_path} --check-setup")
    lines.append("")

    for ep in endpoints:
        credit_str = f'{ep.credit} credit{"s" if ep.credit > 1 else ""}'
        lines.append(f"# {ep.summary} ({credit_str})")

        # Build example command
        args = []
        for p in ep.required_params:
            example = _example_for_param(p)
            args.append(f'{p["flag"]} {example}')
        for p in ep.optional_params:
            if p["name"] == "limit":
                args.append("--limit 20")
            elif p["name"] == "offset":
                continue  # skip offset in examples
            elif p["default"]:
                args.append(f'{p["flag"]} {p["default"]}')

        # Handle POST special cases
        if ep.is_post and ep.has_body:
            if ep.domain == "onchain" and "sql" in ep.subcommand:
                args = ['--sql "SELECT transaction_hash, from_address, value FROM ethereum.transactions WHERE block_number = 21000000 LIMIT 10"']
            elif ep.domain == "onchain" and ep.subcommand == "query":
                args = ["""--body '{"source": "ethereum.transactions", "fields": ["transaction_hash", "from_address", "value"], "filters": [{"field": "block_number", "op": "eq", "value": 21000000}], "limit": 10}'"""]
            elif ep.domain == "social" and ep.subcommand == "tweets":
                args = ['--ids \'["1880293339000000000"]\'']
            elif ep.domain == "web" and ep.subcommand == "fetch":
                args = ["--url https://ethereum.org"]
            elif ep.domain == "wallet" and ep.subcommand == "labels-batch":
                args = ['--addresses \'["0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"]\'']

        args_str = " ".join(args)
        lines.append(f"{script_path} {ep.subcommand} {args_str}")
        lines.append("")

    lines.append("```")
    lines.append("")
    lines.append("## Important Notes")
    lines.append("")
    lines.append(f"- All output is JSON. Data to stdout, errors to stderr.")
    lines.append(f"- Use `--limit` on list commands to control response size.")
    if domain == "token":
        lines.append("- `--chain` is required for `holders` and `transfers`.")
    if domain == "wallet":
        lines.append("- Addresses must be hex format (0x...).")
    if domain == "onchain":
        lines.append("- Only SELECT/WITH queries are allowed. Max 10,000 rows.")
    lines.append("")
    lines.append("## Cost")
    lines.append("")

    # Group by credit cost
    cost_groups = defaultdict(list)
    for ep in endpoints:
        cost_groups[ep.credit].append(ep.subcommand)
    for cost in sorted(cost_groups.keys()):
        cmds = ", ".join(cost_groups[cost])
        lines.append(f"- {cost} credit{'s' if cost > 1 else ''}: {cmds}")
    lines.append("")
    lines.append("## Endpoints Reference")
    lines.append("")
    lines.append(f"See `knowledge/{domain}/endpoints.md` for full parameter details and response formats.")

    return "\n".join(lines) + "\n"


def _domain_description(domain: str, endpoints: list[Endpoint]) -> str:
    """Generate a one-line description for the SKILL.md frontmatter."""
    subcmds = ", ".join(e.subcommand for e in endpoints[:5])
    if len(endpoints) > 5:
        subcmds += f", and {len(endpoints) - 5} more"
    return f"Query {domain} data including {subcmds}"


def _domain_title(domain: str) -> str:
    titles = {
        "market": "Market Analytics",
        "token": "Token-level Analytics",
        "project": "Project Intelligence",
        "wallet": "Wallet Analytics",
        "social": "Social & X/Twitter Data",
        "news": "News & Signals",
        "web": "Web Search & Fetch",
        "onchain": "On-chain SQL Queries",
    }
    return titles.get(domain, f"{domain.title()} Data")


# ---------------------------------------------------------------------------
# endpoints.md generator
# ---------------------------------------------------------------------------

def generate_endpoints_md(domain: str, endpoints: list[Endpoint]) -> str:
    """Generate knowledge/endpoints.md for a domain."""
    lines = []
    lines.append(f"# {domain.title()} Data — Endpoint Reference")
    lines.append("")
    lines.append(f"<!-- Hermod /v1/{domain}/* — standardized {domain} data endpoints -->")
    lines.append("")
    lines.append("## Endpoints")
    lines.append("")
    lines.append(f"All endpoints are under `/v1/{domain}/`. Response envelope: `{{\"data\": [...], \"meta\": {{...}}}}`.")
    lines.append("")
    lines.append("| Endpoint | Description | Key Params | Cost |")
    lines.append("|----------|-------------|------------|------|")

    for ep in endpoints:
        method = ep.method
        path_suffix = ep.path[len(f"/v1/{ep.domain}"):]
        if not path_suffix:
            path_suffix = "/"
        params_str = ", ".join(
            f"`{p['name']}`{' (required)' if p['required'] else ''}"
            for p in ep.params
        )
        if ep.is_post and ep.has_body:
            params_str = "body (required)" + (", " + params_str if params_str else "")
        cost_str = f"{ep.credit} credit{'s' if ep.credit > 1 else ''}"
        lines.append(f"| `{method} {path_suffix}` | {ep.summary} | {params_str} | {cost_str} |")

    lines.append("")

    # Detail sections for endpoints with enum params
    for ep in endpoints:
        enum_params = [p for p in ep.params if p["enum"]]
        if enum_params:
            lines.append(f"### {ep.subcommand} — Valid Parameter Values")
            lines.append("")
            for p in enum_params:
                lines.append(f"**`{p['name']}`**: {', '.join(f'`{v}`' for v in p['enum'])}")
                lines.append("")

    # Chain support if relevant
    chain_endpoints = [ep for ep in endpoints if any(p["name"] == "chain" for p in ep.params)]
    if chain_endpoints:
        lines.append("### Chain Support")
        lines.append("")
        lines.append("| Endpoint | Supported Chains |")
        lines.append("|----------|-----------------|")
        for ep in chain_endpoints:
            chain_param = next(p for p in ep.params if p["name"] == "chain")
            chain_desc = chain_param["description"]
            # Extract chain names from description
            chains = re.findall(r'\b(eth|bsc|polygon|avalanche|fantom|arbitrum|optimism|solana|matic|avax|base)\b', chain_desc.lower())
            chains_str = ", ".join(sorted(set(chains))) if chains else chain_desc
            lines.append(f"| `{ep.subcommand}` | {chains_str} |")
        lines.append("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# File writing
# ---------------------------------------------------------------------------

def write_file(path: str, content: str, dry_run: bool = False):
    """Write content to a file, creating directories as needed."""
    if dry_run:
        print(f"  [DRY-RUN] Would write: {path} ({len(content)} bytes)")
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    print(f"  Wrote: {path} ({len(content)} bytes)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate surf-core CLI scripts from Hermod Swagger spec"
    )
    parser.add_argument(
        "--spec", required=True,
        help="Path to Hermod Swagger 2.0 JSON file"
    )
    parser.add_argument(
        "--output-dir", required=True,
        help="Output directory for CLI scripts (e.g. runtimes/cli/)"
    )
    parser.add_argument(
        "--knowledge-dir", required=True,
        help="Output directory for knowledge files (e.g. knowledge/)"
    )
    parser.add_argument(
        "--domains", default=None,
        help="Comma-separated domain filter (e.g. token,market,social)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be generated without writing files"
    )
    args = parser.parse_args()

    # Parse domain filter
    domain_filter = None
    if args.domains:
        domain_filter = set(d.strip().lower() for d in args.domains.split(","))

    # Load spec
    spec = load_swagger(args.spec)
    print(f"Loaded Swagger spec: {spec['info']['title']} v{spec['info']['version']}")
    print(f"Total paths: {len(spec.get('paths', {}))}")

    # Group endpoints
    groups = group_endpoints(spec, domain_filter)
    print(f"Domains found: {', '.join(sorted(groups.keys()))}")
    for domain, endpoints in sorted(groups.items()):
        print(f"  {domain}: {len(endpoints)} endpoints")

    if not groups:
        print("No matching endpoints found. Check --domains filter.")
        return

    # Generate for each domain
    for domain, endpoints in sorted(groups.items()):
        print(f"\n--- Generating {domain} ---")

        # 1. Bash CLI script
        bash_content = generate_bash_script(domain, endpoints)
        script_dir = os.path.join(args.output_dir, domain, "scripts")
        script_path = os.path.join(script_dir, f"surf-{domain}")
        write_file(script_path, bash_content, args.dry_run)
        if not args.dry_run:
            os.chmod(script_path, 0o755)

        # 2. SKILL.md
        skill_content = generate_skill_md(domain, endpoints)
        skill_path = os.path.join(args.output_dir, domain, "SKILL.md")
        write_file(skill_path, skill_content, args.dry_run)

        # 3. endpoints.md
        endpoints_content = generate_endpoints_md(domain, endpoints)
        knowledge_path = os.path.join(args.knowledge_dir, domain, "endpoints.md")
        write_file(knowledge_path, endpoints_content, args.dry_run)

    print(f"\nDone! Generated {len(groups)} domains.")


if __name__ == "__main__":
    main()
