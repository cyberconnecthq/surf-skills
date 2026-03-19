#!/usr/bin/env python3
"""Create a Datadog dashboard for Vibe Coding session monitoring.

Uses ORDERED (grid) layout. Only queries fields that exist as structured facets.

Available facets:
  urania-agent: @session_id, @user_id, @component, @event_type, @logger, service, status
  muninn-api PREVIEW_PERF: @path, @status, @http_ms, @resolve_ms, @proxy_ms, @total_ms,
                           @db_ms, @sandbox_check_ms, @sandbox_active, @target, @caller

NOT faceted (in message text only — use log stream to view):
  LLM_PERF: model, ttft_ms, total_ms, in, out, cache_read
  STARTUP_PERF: spawn_ready_ms, prewarm_import_ms

Usage:
    cd surf-skills/odin-dev-datadog
    uv run python scripts/create_vibe_dashboard.py [--update ID] [--delete ID]
"""

import argparse
import json
import sys
from pathlib import Path

from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v1.api.dashboards_api import DashboardsApi
from datadog_api_client.v1.model.dashboard import Dashboard
from datadog_api_client.v1.model.dashboard_layout_type import DashboardLayoutType
from datadog_api_client.v1.model.log_query_definition import LogQueryDefinition
from datadog_api_client.v1.model.log_query_definition_group_by import LogQueryDefinitionGroupBy
from datadog_api_client.v1.model.log_query_definition_group_by_sort import LogQueryDefinitionGroupBySort
from datadog_api_client.v1.model.log_query_definition_search import LogQueryDefinitionSearch
from datadog_api_client.v1.model.log_stream_widget_definition import LogStreamWidgetDefinition
from datadog_api_client.v1.model.log_stream_widget_definition_type import LogStreamWidgetDefinitionType
from datadog_api_client.v1.model.logs_query_compute import LogsQueryCompute
from datadog_api_client.v1.model.note_widget_definition import NoteWidgetDefinition
from datadog_api_client.v1.model.note_widget_definition_type import NoteWidgetDefinitionType
from datadog_api_client.v1.model.query_value_widget_definition import QueryValueWidgetDefinition
from datadog_api_client.v1.model.query_value_widget_definition_type import QueryValueWidgetDefinitionType
from datadog_api_client.v1.model.query_value_widget_request import QueryValueWidgetRequest
from datadog_api_client.v1.model.timeseries_widget_definition import TimeseriesWidgetDefinition
from datadog_api_client.v1.model.timeseries_widget_definition_type import TimeseriesWidgetDefinitionType
from datadog_api_client.v1.model.timeseries_widget_request import TimeseriesWidgetRequest
from datadog_api_client.v1.model.toplist_widget_definition import ToplistWidgetDefinition
from datadog_api_client.v1.model.toplist_widget_definition_type import ToplistWidgetDefinitionType
from datadog_api_client.v1.model.toplist_widget_request import ToplistWidgetRequest
from datadog_api_client.v1.model.widget import Widget
from datadog_api_client.v1.model.widget_layout import WidgetLayout
from datadog_api_client.v1.model.widget_text_align import WidgetTextAlign
from datadog_api_client.v1.model.group_widget_definition import GroupWidgetDefinition
from datadog_api_client.v1.model.group_widget_definition_type import GroupWidgetDefinitionType
from datadog_api_client.v1.model.widget_layout_type import WidgetLayoutType


def load_config():
    cfg_path = Path.home() / ".ddlog.json"
    if not cfg_path.exists():
        print(f"Error: {cfg_path} not found.")
        sys.exit(1)
    with open(cfg_path) as f:
        return json.load(f)


def make_client(cfg):
    config = Configuration()
    config.api_key["apiKeyAuth"] = cfg["api_key"]
    config.api_key["appKeyAuth"] = cfg["app_key"]
    config.server_variables["site"] = cfg.get("site", "datadoghq.com")
    return config


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def _lq(query, agg="count", facet=None, interval=0, group_by=None):
    kw = {"aggregation": agg}
    if facet:
        kw["facet"] = facet
    if interval:
        kw["interval"] = interval
    return LogQueryDefinition(
        search=LogQueryDefinitionSearch(query=query),
        compute=LogsQueryCompute(**kw),
        group_by=group_by or [],
        index="*",
    )


def _gb(facet, limit=10):
    return LogQueryDefinitionGroupBy(
        facet=facet, limit=limit,
        sort=LogQueryDefinitionGroupBySort(aggregation="count", order="desc"),
    )


# ---------------------------------------------------------------------------
# Widget factories
# ---------------------------------------------------------------------------

def _qv(title, query, agg="count", facet=None):
    """Query-value card — auto-sized by grid."""
    return Widget(definition=QueryValueWidgetDefinition(
        type=QueryValueWidgetDefinitionType.QUERY_VALUE,
        title=title, autoscale=True, precision=0,
        text_align=WidgetTextAlign.CENTER,
        requests=[QueryValueWidgetRequest(log_query=_lq(query, agg=agg, facet=facet))],
    ))


def _ts(title, query, agg="count", facet=None, group_by=None):
    """Timeseries chart."""
    return Widget(definition=TimeseriesWidgetDefinition(
        type=TimeseriesWidgetDefinitionType.TIMESERIES,
        title=title, show_legend=True,
        requests=[TimeseriesWidgetRequest(
            log_query=_lq(query, agg=agg, facet=facet, interval=60, group_by=group_by),
        )],
    ))


def _top(title, query, facet, limit=10):
    """Toplist."""
    return Widget(definition=ToplistWidgetDefinition(
        type=ToplistWidgetDefinitionType.TOPLIST,
        title=title,
        requests=[ToplistWidgetRequest(log_query=_lq(query, group_by=[_gb(facet, limit)]))],
    ))



def _group(title, widgets):
    """Collapsible group section."""
    return Widget(definition=GroupWidgetDefinition(
        type=GroupWidgetDefinitionType.GROUP,
        title=title,
        layout_type=WidgetLayoutType.ORDERED,
        widgets=widgets,
    ))


# ---------------------------------------------------------------------------
# Service filters
# ---------------------------------------------------------------------------

U = "service:urania-agent"
M = "service:muninn-api"
VIBE = f"({U} OR {M})"
HAS_SID = f"{VIBE} @session_id:*"


def build_widgets():
    return [
        # ══════════════════════════════════════════════════════════
        # ROW 1 — KPI Numbers
        # ══════════════════════════════════════════════════════════
        _group("Key Metrics", [
            _qv("Sessions", HAS_SID, agg="cardinality", facet="@session_id"),
            _qv("LLM Calls", f"{U} LLM_PERF"),
            _qv("SSE Events", f'{U} "Event #"'),
            _qv("Preview Requests", f"{M} PREVIEW_PERF"),
            _qv("Errors", f"{VIBE} status:error"),
            _qv("Warnings", f"{VIBE} status:warn"),
        ]),

        # ══════════════════════════════════════════════════════════
        # ROW 2 — Realtime Charts
        # ══════════════════════════════════════════════════════════
        _group("Activity & Health", [
            # Session & log volume
            _ts("Sessions Over Time", HAS_SID,
                agg="cardinality", facet="@session_id"),
            _ts("Log Volume by Service", VIBE,
                group_by=[_gb("service", 5)]),

            # SSE event breakdown — shows each stage (turn_done, resource_usage, etc.)
            _ts("SSE Events by Type", f'{U} "Event #"',
                group_by=[_gb("@event_type", 10)]),
            _ts("Errors Over Time by Service", f"{VIBE} status:error",
                group_by=[_gb("service", 5)]),

            # Preview proxy — has real numeric facets
            _ts("Preview Latency avg (http_ms)", f"{M} PREVIEW_PERF proxy_preview",
                agg="avg", facet="@http_ms"),
            _ts("Preview Latency p95 (http_ms)", f"{M} PREVIEW_PERF proxy_preview",
                agg="percentile(0.95)", facet="@http_ms"),
        ]),

        # ══════════════════════════════════════════════════════════
        # ROW 3 — Deeper breakdowns
        # ══════════════════════════════════════════════════════════
        _group("Breakdown", [
            _ts("LLM Calls Over Time", f"{U} LLM_PERF"),
            _ts("Sandbox Spawns", f"{U} STARTUP_PERF"),

            _top("Top Components", VIBE, "@component"),
            _top("Top Error Components", f"{VIBE} status:error", "@component"),

            _top("Preview Top Paths", f"{M} PREVIEW_PERF proxy_preview", "@path"),
            _top("SSE Event Types", f'{U} "Event #"', "@event_type"),
        ]),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--update", metavar="ID")
    parser.add_argument("--delete", metavar="ID")
    args = parser.parse_args()

    cfg = load_config()
    config = make_client(cfg)

    with ApiClient(config) as client:
        api = DashboardsApi(client)

        if args.delete:
            api.delete_dashboard(dashboard_id=args.delete)
            print(f"Deleted {args.delete}")
            return

        dashboard = Dashboard(
            title="Vibe Coding — Session Monitor",
            layout_type=DashboardLayoutType.ORDERED,
            description="Vibe Coding session monitoring: urania-agent + muninn-api. "
                        "KPIs → realtime charts → log streams.",
            widgets=build_widgets(),
            tags=["team:surf", "ai:vibe-coding"],
        )

        if args.update:
            result = api.update_dashboard(dashboard_id=args.update, body=dashboard)
            print(f"Updated: {result.title}")
        else:
            result = api.create_dashboard(body=dashboard)
            print(f"Created: {result.title}")

        print(f"ID: {result.id}")
        print(f"URL: https://app.{cfg.get('site', 'datadoghq.com')}/dashboard/{result.id}")


if __name__ == "__main__":
    main()
