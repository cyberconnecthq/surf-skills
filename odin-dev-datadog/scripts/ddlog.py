#!/usr/bin/env python3
"""Datadog log viewer for Surf platform debugging.

Query logs by session_id, user_id, or raw Datadog query.
Output format mimics kubectl logs for familiarity.

Requires: pip install datadog-api-client
Config: DD_API_KEY and DD_APP_KEY env vars, or ~/.ddlog.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from datadog_api_client import ApiClient, Configuration
    from datadog_api_client.v2.api.logs_api import LogsApi
    from datadog_api_client.v2.model.logs_list_request import LogsListRequest
    from datadog_api_client.v2.model.logs_list_request_page import LogsListRequestPage
    from datadog_api_client.v2.model.logs_query_filter import LogsQueryFilter
    from datadog_api_client.v2.model.logs_sort import LogsSort
except ImportError:
    print("ERROR: datadog-api-client not installed. Run: pip install datadog-api-client", file=sys.stderr)
    sys.exit(1)


# -- Colors ------------------------------------------------------------------

class C:
    RESET = "\033[0m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    GRAY = "\033[90m"
    BOLD = "\033[1m"
    WHITE = "\033[37m"

LEVEL_COLORS = {
    "error": C.RED,
    "critical": C.RED + C.BOLD,
    "warn": C.YELLOW,
    "warning": C.YELLOW,
    "info": C.GREEN,
    "debug": C.GRAY,
    "ok": C.GREEN,
}

NO_COLOR = os.environ.get("NO_COLOR") is not None


def colorize(text, color):
    if NO_COLOR:
        return text
    return f"{color}{text}{C.RESET}"


# -- Config -------------------------------------------------------------------

CONFIG_PATH = Path.home() / ".ddlog.json"


def load_config():
    """Load DD keys from env vars or ~/.ddlog.json."""
    api_key = os.environ.get("DD_API_KEY")
    app_key = os.environ.get("DD_APP_KEY")
    site = os.environ.get("DD_SITE", "datadoghq.com")

    if not api_key or not app_key:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                cfg = json.load(f)
            api_key = api_key or cfg.get("api_key")
            app_key = app_key or cfg.get("app_key")
            site = cfg.get("site", site)

    if not api_key or not app_key:
        print("ERROR: DD_API_KEY and DD_APP_KEY required.", file=sys.stderr)
        print(f"Set env vars or create {CONFIG_PATH} with:", file=sys.stderr)
        print('  {"api_key": "...", "app_key": "...", "site": "datadoghq.com"}', file=sys.stderr)
        sys.exit(1)

    return api_key, app_key, site


# -- Time parsing -------------------------------------------------------------

def parse_time_range(time_str):
    """Parse relative time like '1h', '30m', '2d' into Datadog-compatible string."""
    return f"now-{time_str}"


# -- Query building -----------------------------------------------------------

def build_query(args):
    """Build Datadog query string from CLI args."""
    parts = []

    if args.command == "session":
        parts.append(f"@session_id:{args.id}")
    elif args.command == "user":
        parts.append(f"@user_id:{args.id}")
    elif args.command == "query":
        parts.append(args.raw_query)

    if args.service:
        parts.append(f"service:{args.service}")
    if args.level:
        parts.append(f"status:{args.level}")
    if args.extra:
        parts.append(args.extra)

    return " ".join(parts)


# -- Log formatting -----------------------------------------------------------

def format_log(log_entry, verbose=False):
    """Format a single log entry kubectl-style.

    Compact: TIMESTAMP [SERVICE] LEVEL  MESSAGE  key=value key=value
    Verbose: adds full attributes dump
    """
    attrs = log_entry.attributes
    ts_raw = getattr(attrs, "timestamp", "") or attrs.get("timestamp", "")
    service = getattr(attrs, "service", "?") or attrs.get("service", "?")
    status = getattr(attrs, "status", "?") or attrs.get("status", "?")
    message = getattr(attrs, "message", "") or attrs.get("message", "")
    log_attrs = getattr(attrs, "attributes", {}) or attrs.get("attributes", {}) or {}
    if hasattr(log_attrs, "to_dict"):
        log_attrs = log_attrs.to_dict()

    # Parse timestamp to compact format
    if isinstance(ts_raw, datetime):
        ts = ts_raw.strftime("%m-%d %H:%M:%S")
    elif ts_raw:
        try:
            dt = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
            ts = dt.strftime("%m-%d %H:%M:%S")
        except (ValueError, AttributeError):
            ts = str(ts_raw)[:19]
    else:
        ts = "?"

    # Color the level
    level_str = status.upper().ljust(5)
    level_color = LEVEL_COLORS.get(status.lower(), "")
    level_display = colorize(level_str, level_color)

    # Service tag
    svc_display = colorize(f"[{service}]", C.CYAN)

    # Timestamp
    ts_display = colorize(ts, C.GRAY)

    # Extract key context fields for inline display
    ctx_fields = []
    for key in ("session_id", "user_id", "trace_id", "request_id",
                "endpoint", "path", "method", "duration_ms",
                "http.status_code", "error.kind", "error.message"):
        val = _deep_get(log_attrs, key)
        if val is not None:
            short_key = key.split(".")[-1] if "." in key else key
            ctx_fields.append(f"{colorize(short_key, C.GRAY)}={val}")

    # Truncate message for single line
    msg = message.replace("\n", " ").strip()
    if len(msg) > 200 and not verbose:
        msg = msg[:200] + "..."

    line = f"{ts_display} {svc_display} {level_display} {msg}"
    if ctx_fields:
        line += "  " + " ".join(ctx_fields)

    if verbose:
        # Dump all attributes below the main line
        filtered = {k: v for k, v in log_attrs.items()
                    if k not in ("message",) and v is not None}
        if filtered:
            dumped = json.dumps(filtered, indent=2, default=str, ensure_ascii=False)
            indent = "    "
            line += "\n" + "\n".join(indent + l for l in dumped.split("\n"))

    return line


def _deep_get(d, dotted_key):
    """Get nested dict value by dotted key like 'http.status_code'."""
    keys = dotted_key.split(".")
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k)
        else:
            return None
    return d


# -- API call -----------------------------------------------------------------

def fetch_logs(api_key, app_key, site, query, time_from, time_to, limit, sort_order):
    """Fetch logs from Datadog API with cursor pagination."""
    config = Configuration()
    config.api_key["apiKeyAuth"] = api_key
    config.api_key["appKeyAuth"] = app_key
    config.server_variables["site"] = site

    sort = LogsSort.TIMESTAMP_ASCENDING if sort_order == "asc" else LogsSort.TIMESTAMP_DESCENDING

    all_logs = []
    cursor = None

    with ApiClient(config) as client:
        api = LogsApi(client)

        while True:
            page_kwargs = {"limit": min(limit - len(all_logs), 1000)}
            if cursor:
                page_kwargs["cursor"] = cursor

            body = LogsListRequest(
                filter=LogsQueryFilter(
                    query=query,
                    _from=time_from,
                    to=time_to,
                ),
                sort=sort,
                page=LogsListRequestPage(**page_kwargs),
            )

            resp = api.list_logs(body=body)
            data = resp.data or []
            all_logs.extend(data)

            if len(all_logs) >= limit:
                break

            meta = resp.meta
            try:
                cursor = meta.page.after
                if not cursor:
                    break
            except Exception:
                break

    return all_logs[:limit]


# -- Stats summary -----------------------------------------------------------

def print_stats(logs):
    """Print a brief stats summary."""
    if not logs:
        print(colorize("No logs found.", C.YELLOW))
        return

    level_counts = {}
    services = set()
    for log in logs:
        attrs = log.attributes
        status = attrs.get("status", "unknown")
        service = attrs.get("service", "?")
        level_counts[status] = level_counts.get(status, 0) + 1
        services.add(service)

    parts = [f"{colorize(str(len(logs)), C.BOLD)} logs"]
    parts.append(f"services: {', '.join(sorted(services))}")
    for level in ("error", "warn", "info", "debug"):
        count = level_counts.get(level, 0)
        if count > 0:
            color = LEVEL_COLORS.get(level, "")
            parts.append(f"{colorize(level, color)}={count}")

    print(colorize("--- ", C.GRAY) + " | ".join(parts) + colorize(" ---", C.GRAY))


# -- Main ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Datadog log viewer for Surf platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  ddlog session abc-123-def
  ddlog user 550e8400-e29b --service urania --time 2h
  ddlog query "status:error" --service hermod --time 30m --level error
  ddlog session abc-123 --verbose
  ddlog query "@endpoint:/v1/agent/chat AND status:error" --time 4h
""",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # session subcommand
    p_session = sub.add_parser("session", help="Query by session_id")
    p_session.add_argument("id", help="Session ID to filter")

    # user subcommand
    p_user = sub.add_parser("user", help="Query by user_id")
    p_user.add_argument("id", help="User ID to filter")

    # query subcommand
    p_query = sub.add_parser("query", help="Raw Datadog query")
    p_query.add_argument("raw_query", help="Datadog query string")

    # Common options
    for p in (p_session, p_user, p_query):
        p.add_argument("-s", "--service", choices=["urania", "hermod"], help="Filter by service")
        p.add_argument("-t", "--time", default="1h", help="Time range (default: 1h, e.g. 30m, 2h, 1d)")
        p.add_argument("-l", "--level", choices=["debug", "info", "warn", "error"], help="Min log level")
        p.add_argument("-n", "--limit", type=int, default=500, help="Max logs to fetch (default: 500)")
        p.add_argument("-v", "--verbose", action="store_true", help="Show full log attributes")
        p.add_argument("--sort", choices=["asc", "desc"], default="asc", help="Sort order (default: asc)")
        p.add_argument("--json", action="store_true", help="Output raw JSON")
        p.add_argument("--stats-only", action="store_true", help="Only show stats summary")
        p.add_argument("--extra", help="Additional Datadog query to AND with")

    args = parser.parse_args()

    # Load config
    api_key, app_key, site = load_config()

    # Build query
    query = build_query(args)
    time_from = parse_time_range(args.time)
    time_to = "now"

    # Show what we're querying
    print(colorize(f"Query: {query}", C.GRAY), file=sys.stderr)
    print(colorize(f"Range: {time_from} → {time_to}", C.GRAY), file=sys.stderr)
    print(file=sys.stderr)

    # Fetch
    logs = fetch_logs(api_key, app_key, site, query, time_from, time_to, args.limit, args.sort)

    # Output
    if args.json:
        for log in logs:
            print(json.dumps(log.to_dict(), default=str, ensure_ascii=False))
    elif args.stats_only:
        print_stats(logs)
    else:
        print_stats(logs)
        print(file=sys.stderr)
        for log in logs:
            print(format_log(log, verbose=args.verbose))


if __name__ == "__main__":
    main()
