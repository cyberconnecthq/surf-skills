#!/usr/bin/env python3
"""Create a Datadog dashboard for Hermod API gateway monitoring.

Based on API_REQ structured logs with fields:
  method, path, status, latency_ms, response_size, ip, user_agent,
  query, user_id, event_source, credits, plan, dd.trace_id, dd.span_id

Usage:
    cd surf-skills/odin-dev-datadog
    uv run python scripts/create_hermod_dashboard.py [--update ID] [--delete ID]
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
from datadog_api_client.v1.model.logs_query_compute import LogsQueryCompute
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

H = "service:hermod-api API_REQ"  # base query — note service is hermod-api not hermod


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


def _gb(facet, limit=10, agg="count"):
    return LogQueryDefinitionGroupBy(
        facet=facet, limit=limit,
        sort=LogQueryDefinitionGroupBySort(aggregation=agg, order="desc"),
    )


# ---------------------------------------------------------------------------
# Widget factories
# ---------------------------------------------------------------------------

def _qv(title, query=H, agg="count", facet=None):
    return Widget(definition=QueryValueWidgetDefinition(
        type=QueryValueWidgetDefinitionType.QUERY_VALUE,
        title=title, autoscale=True, precision=0,
        text_align=WidgetTextAlign.CENTER,
        requests=[QueryValueWidgetRequest(log_query=_lq(query, agg=agg, facet=facet))],
    ))


def _ts(title, query=H, agg="count", facet=None, group_by=None):
    return Widget(definition=TimeseriesWidgetDefinition(
        type=TimeseriesWidgetDefinitionType.TIMESERIES,
        title=title, show_legend=True,
        requests=[TimeseriesWidgetRequest(
            log_query=_lq(query, agg=agg, facet=facet, interval=60, group_by=group_by),
        )],
    ))


def _top(title, query=H, facet="@path", limit=10, agg="count"):
    return Widget(definition=ToplistWidgetDefinition(
        type=ToplistWidgetDefinitionType.TOPLIST,
        title=title,
        requests=[ToplistWidgetRequest(log_query=_lq(query, group_by=[_gb(facet, limit, agg)]))],
    ))


def _group(title, widgets):
    return Widget(definition=GroupWidgetDefinition(
        type=GroupWidgetDefinitionType.GROUP,
        title=title,
        layout_type=WidgetLayoutType.ORDERED,
        widgets=widgets,
    ))


# ---------------------------------------------------------------------------
# Dashboard definition
# ---------------------------------------------------------------------------

def build_widgets():
    return [
        # ── ROW 1: KPI Numbers ────────────────────────────────────
        _group("Key Metrics", [
            _qv("Total Requests"),
            _qv("Unique Users", agg="cardinality", facet="@user_id"),
            _qv("Errors (4xx+5xx)", query=f"{H} @status:>=400"),
            _qv("5xx Errors", query=f"{H} @status:>=500"),
            _qv("Avg Latency (ms)", agg="avg", facet="@latency_ms"),
            _qv("Total Credits", agg="sum", facet="@credits"),
        ]),

        # ── ROW 2: Traffic & Latency ──────────────────────────────
        _group("Traffic & Performance", [
            _ts("Requests Over Time"),
            _ts("Requests by Status Code",
                group_by=[_gb("@status", 5)]),
            _ts("Avg Latency Over Time (ms)",
                agg="avg", facet="@latency_ms"),
            _ts("P95 Latency Over Time (ms)",
                agg="percentile(0.95)", facet="@latency_ms"),
            _ts("Error Rate Over Time",
                query=f"{H} @status:>=400"),
            _ts("Avg Response Size Over Time (bytes)",
                agg="avg", facet="@response_size"),
        ]),

        # ── ROW 3: Endpoints & Users ─────────────────────────────
        _group("Endpoints & Usage", [
            _top("Top Endpoints by Requests", facet="@path"),
            _top("Slowest Endpoints (avg latency)",
                 facet="@path", agg="avg"),
            _top("Top Endpoints by Errors",
                 query=f"{H} @status:>=400", facet="@path"),
            _top("Top Users by Requests", facet="@user_id"),
            _top("Top Event Sources", facet="@event_source"),
            _top("Requests by Plan", facet="@plan"),
        ]),

        # ── ROW 4: Credits & Billing ─────────────────────────────
        _group("Credits & Billing", [
            _ts("Credits Consumed Over Time",
                agg="sum", facet="@credits"),
            _ts("Credits by Plan",
                agg="sum", facet="@credits",
                group_by=[_gb("@plan", 5)]),
            _top("Top Credit Consumers (users)",
                 facet="@user_id", agg="sum"),
            _top("Credit Consumption by Endpoint",
                 facet="@event_source", agg="sum"),
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
            title="Hermod — API Gateway Monitor",
            layout_type=DashboardLayoutType.ORDERED,
            description="Hermod API gateway monitoring based on API_REQ structured logs. "
                        "Covers request throughput, latency, error rates, endpoint usage, "
                        "user activity, and credit consumption.",
            widgets=build_widgets(),
            tags=["team:surf"],
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
