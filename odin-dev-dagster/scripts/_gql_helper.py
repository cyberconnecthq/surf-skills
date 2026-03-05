#!/usr/bin/env python3
"""Dagster GraphQL helper — runs inside the webserver pod via kubectl exec."""
import json
import sys
import urllib.request
from datetime import datetime

GQL_URL = "http://localhost:80/graphql"


def gql(query):
    req = urllib.request.Request(
        GQL_URL,
        data=json.dumps({"query": query}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read())
    except Exception as e:
        body = e.read().decode()[:1000] if hasattr(e, "read") else str(e)
        print("GraphQL error: " + body, file=sys.stderr)
        sys.exit(1)


def ts_fmt(epoch, fmt="%Y-%m-%d %H:%M:%S"):
    if not epoch:
        return "?"
    try:
        return datetime.fromtimestamp(float(epoch)).strftime(fmt)
    except (ValueError, OSError):
        return "?"


def duration_fmt(start, end):
    if not start or not end:
        return ""
    d = end - start
    if d < 60:
        return f"{d:.0f}s"
    elif d < 3600:
        return f"{d/60:.0f}m"
    else:
        return f"{d/3600:.1f}h"


def cmd_run_detail(run_id, log_limit=50, step_filter=None):
    r = gql(
        """query RunDetail {
        runOrError(runId: "%s") {
            ... on Run {
                runId jobName status startTime endTime
                repositoryOrigin { repositoryLocationName repositoryName }
                tags { key value }
                stepStats {
                    stepKey
                    status
                    startTime
                    endTime
                }
            }
            ... on RunNotFoundError { message }
            ... on PythonError { message }
        }
    }"""
        % run_id
    )

    run_data = r["data"]["runOrError"]
    if "runId" not in run_data:
        print("Error: " + run_data.get("message", "Unknown error"))
        sys.exit(1)

    loc = run_data.get("repositoryOrigin", {}).get("repositoryLocationName", "?")
    print(f"Run:      {run_data['runId']}")
    print(f"Job:      {loc}/{run_data['jobName']}")
    print(f"Status:   {run_data['status']}")
    print(f"Start:    {ts_fmt(run_data.get('startTime'))}")
    print(f"End:      {ts_fmt(run_data.get('endTime'))}")
    dur = duration_fmt(run_data.get("startTime"), run_data.get("endTime"))
    if dur:
        print(f"Duration: {dur}")
    tags = run_data.get("tags", [])
    useful = [t for t in tags if not t["key"].startswith("dagster/")]
    if useful:
        print(f"Tags:     {', '.join(t['key']+'='+t['value'] for t in useful)}")

    # Step stats summary
    step_stats = run_data.get("stepStats") or []
    if step_stats:
        print()
        status_icons = {"SUCCEEDED": "OK", "FAILED": "FAIL", "SKIPPED": "SKIP", "IN_PROGRESS": "RUN"}
        print("Steps:")
        for s in step_stats:
            icon = status_icons.get(s["status"], s["status"][:4])
            step_dur = duration_fmt(s.get("startTime"), s.get("endTime"))
            print(f"  [{icon:>4}] {s['stepKey']:<50} {step_dur}")

    print()
    _print_logs(run_id, log_limit, False, step_filter)


def cmd_run_logs(run_id, log_limit=200, failures_only=False, step_filter=None):
    _print_logs(run_id, log_limit, failures_only, step_filter)


def _print_logs(run_id, log_limit, failures_only, step_filter=None):
    r = gql(
        """query RunLogs {
        logsForRun(runId: "%s") {
            ... on EventConnection {
                events {
                    __typename
                    ... on MessageEvent { message timestamp }
                    ... on EngineEvent { message timestamp }
                    ... on RunFailureEvent { message timestamp }
                    ... on RunStartEvent { message timestamp }
                    ... on RunSuccessEvent { message timestamp }
                    ... on ExecutionStepStartEvent { message timestamp stepKey }
                    ... on ExecutionStepSuccessEvent { message timestamp stepKey }
                    ... on ExecutionStepFailureEvent {
                        message timestamp stepKey
                        error {
                            message
                            stack
                            className
                            cause { message className stack }
                        }
                        errorSource
                        failureMetadata {
                            label
                            description
                            metadataEntries {
                                __typename
                                label
                                description
                                ... on TextMetadataEntry { text }
                                ... on MarkdownMetadataEntry { mdStr }
                                ... on JsonMetadataEntry { jsonString }
                                ... on PathMetadataEntry { path }
                            }
                        }
                    }
                    ... on LogMessageEvent { message timestamp stepKey }
                    ... on LogsCapturedEvent {
                        message timestamp stepKeys fileKey logKey pid
                    }
                }
            }
        }
    }"""
        % run_id
    )

    events = r["data"]["logsForRun"]["events"]

    # Filter by step name if specified
    if step_filter:
        step_lower = step_filter.lower()
        events = [
            e for e in events
            if step_lower in (e.get("stepKey") or "").lower()
            or step_lower in str(e.get("stepKeys") or []).lower()
            or e.get("__typename") in ("RunFailureEvent", "RunStartEvent", "RunSuccessEvent")
        ]

    failure_types = {
        "RunFailureEvent",
        "ExecutionStepFailureEvent",
        "EngineEvent",
    }
    if failures_only:
        events = [
            e
            for e in events
            if e.get("__typename") in failure_types and (e.get("message") or e.get("error"))
        ]

    shown = events[-log_limit:] if len(events) > log_limit else events
    print(f"Log events ({len(events)} total, showing last {len(shown)}):")
    print("-" * 80)
    for e in shown:
        msg = e.get("message", "")
        typename = e.get("__typename", "")
        step = e.get("stepKey", "")
        ts = ""
        if e.get("timestamp"):
            try:
                ts = datetime.fromtimestamp(
                    float(e["timestamp"]) / 1000
                ).strftime("%H:%M:%S")
            except (ValueError, OSError):
                pass
        prefix = f"[{step}] " if step else ""
        label = typename.replace("Event", "")

        # LogsCapturedEvent: show step keys and fileKey
        if typename == "LogsCapturedEvent":
            step_keys = e.get("stepKeys") or []
            file_key = e.get("fileKey") or ""
            pid = e.get("pid")
            print(f"  {ts} {'LogsCaptured':<22} steps={step_keys} fileKey={file_key} pid={pid}")
            continue

        if msg:
            print(f"  {ts} {label:<22} {prefix}{msg[:300]}")

        # ExecutionStepFailureEvent: print full error details
        if typename == "ExecutionStepFailureEvent":
            pad = "  " + " " * 8

            # failureMetadata (dbt output, custom metadata, etc.)
            fm = e.get("failureMetadata")
            if fm:
                entries = fm.get("metadataEntries") or []
                for me in entries:
                    label = me.get("label", "")
                    content = me.get("text") or me.get("mdStr") or me.get("jsonString") or me.get("path") or ""
                    if content:
                        print()
                        print(f"{pad}[{label}]")
                        for line in content.split("\n"):
                            print(f"{pad}  {line}")

            # error.message and stack trace
            err = e.get("error")
            if err:
                err_class = err.get("className") or ""
                err_msg = err.get("message") or ""
                # Only print error message if it adds info beyond failureMetadata
                if err_msg and err_msg.strip() and err_msg not in (msg or ""):
                    print()
                    print(f"{pad}Error: {err_class}")
                    for line in err_msg.split("\n"):
                        print(f"{pad}  {line}")

                stack = err.get("stack") or []
                if stack:
                    print()
                    print(f"{pad}Stack trace:")
                    for line in stack[-8:]:
                        for sl in line.rstrip().split("\n"):
                            print(f"{pad}  {sl[:200]}")

                cause = err.get("cause")
                if cause and cause.get("message"):
                    print()
                    print(f"{pad}Caused by: {cause.get('className', '')}")
                    for line in (cause.get("message") or "").split("\n")[:10]:
                        print(f"{pad}  {line}")

            print()


def cmd_job_runs(job_name, limit=10, status_filter=None):
    """Show job overview + recent runs — the primary entry point for job investigation."""

    # 1. Find job location and associated sensors/schedules
    r = gql("""query {
        workspaceOrError {
            ... on Workspace {
                locationEntries {
                    name
                    locationOrLoadError {
                        ... on RepositoryLocation {
                            repositories {
                                name
                                jobs { name }
                                schedules {
                                    name
                                    scheduleState { status }
                                    pipelineName
                                }
                                sensors {
                                    name
                                    sensorState { status }
                                    targets { pipelineName }
                                }
                            }
                        }
                    }
                }
            }
        }
    }""")

    entries = r["data"]["workspaceOrError"]["locationEntries"]
    job_loc = None
    job_repo = None
    job_schedules = []
    job_sensors = []

    for loc in entries:
        loe = loc.get("locationOrLoadError", {})
        for repo in loe.get("repositories", []):
            for job in repo.get("jobs", []):
                if job["name"] == job_name:
                    job_loc = loc["name"]
                    job_repo = repo["name"]
                    for s in repo.get("schedules", []):
                        if s.get("pipelineName") == job_name:
                            job_schedules.append(s)
                    for s in repo.get("sensors", []):
                        targets = s.get("targets") or []
                        for t in targets:
                            if t.get("pipelineName") == job_name:
                                job_sensors.append(s)

    if not job_loc:
        # Try substring match
        matches = []
        for loc in entries:
            loe = loc.get("locationOrLoadError", {})
            for repo in loe.get("repositories", []):
                for job in repo.get("jobs", []):
                    if job_name.lower() in job["name"].lower():
                        matches.append(f"  {loc['name']}/{job['name']}")
        if matches:
            print(f"Job '{job_name}' not found. Did you mean:", file=sys.stderr)
            for m in matches:
                print(m, file=sys.stderr)
        else:
            print(f"Job '{job_name}' not found.", file=sys.stderr)
        sys.exit(1)

    # Print job header
    print(f"Job:      {job_loc}/{job_name}")
    for s in job_schedules:
        status = s.get("scheduleState", {}).get("status", "?")
        icon = "ON" if status == "RUNNING" else "OFF"
        print(f"Schedule: [{icon}] {s['name']}")
    for s in job_sensors:
        status = s.get("sensorState", {}).get("status", "?")
        icon = "ON" if status == "RUNNING" else "OFF"
        print(f"Sensor:   [{icon}] {s['name']}")
    print()

    # 2. Query recent runs for this job (server-side filter)
    filter_parts = [f'pipelineName: "{job_name}"']
    if status_filter:
        filter_parts.append(f"statuses: [{status_filter}]")
    filter_str = ", ".join(filter_parts)

    r = gql("""query {
        runsOrError(filter: {%s}, limit: %d) {
            ... on Runs {
                count
                results {
                    runId jobName status startTime endTime
                    tags { key value }
                }
            }
        }
    }""" % (filter_str, limit))

    runs_data = r["data"]["runsOrError"]
    results = runs_data.get("results", [])
    total = runs_data.get("count", 0)

    status_icons = {
        "SUCCESS": " OK ", "FAILURE": "FAIL", "STARTED": " RUN",
        "CANCELED": "CNCL", "QUEUED": "WAIT", "CANCELING": "STOP",
        "STARTING": "INIT",
    }

    print(f"Runs (showing {len(results)} of {total}):")
    print(f"{'ID':<10}  {'Status':>6}  {'Launched by':<24}  {'Created':<14}  {'Duration':>8}")
    print("-" * 72)

    for run in results:
        run_id = run["runId"][:8]
        status = status_icons.get(run["status"], run["status"][:4])

        launched_by = "Manual"
        for tag in run.get("tags", []):
            if tag["key"] == "dagster/sensor_name":
                launched_by = tag["value"]
            elif tag["key"] == "dagster/schedule_name":
                launched_by = tag["value"]

        created = ts_fmt(run.get("startTime"), "%m-%d %H:%M")
        duration = duration_fmt(run.get("startTime"), run.get("endTime"))

        print(f"{run_id:<10}  [{status}]  {launched_by:<24}  {created:<14}  {duration:>8}")


def cmd_job_info(location, job_name, repository="__repository__"):
    """Show job config schema, presets, tags — everything needed before launching."""
    r = gql(
        """query JobInfo {
        pipelineOrError(params: {
            repositoryLocationName: "%s"
            repositoryName: "%s"
            pipelineName: "%s"
        }) {
            ... on Pipeline {
                name
                description
                presets { name runConfigYaml tags { key value } }
                modes {
                    name
                    resources {
                        name
                        description
                        configField {
                            configType {
                                key
                                description
                                ... on CompositeConfigType {
                                    fields {
                                        name
                                        isRequired
                                        description
                                        defaultValueAsJson
                                        configType { key description }
                                    }
                                }
                            }
                        }
                    }
                }
                tags { key value }
            }
            ... on PipelineNotFoundError { message }
            ... on PythonError { message }
        }
    }"""
        % (location, repository, job_name)
    )

    pipe = r["data"]["pipelineOrError"]
    if "name" not in pipe:
        print("Error: " + pipe.get("message", "Unknown"))
        sys.exit(1)

    print(f"Job:      {location}/{pipe['name']}")
    if pipe.get("description"):
        print(f"Desc:     {pipe['description'][:200]}")

    tags = pipe.get("tags", [])
    if tags:
        print(f"Tags:     {', '.join(t['key']+'='+t['value'] for t in tags)}")

    # Presets
    presets = pipe.get("presets", [])
    print()
    if presets:
        print(f"Presets ({len(presets)}):")
        for p in presets:
            config_yaml = p.get("runConfigYaml", "").strip()
            print(f"  [{p['name']}]")
            if config_yaml:
                for line in config_yaml.split("\n"):
                    print(f"    {line}")
            else:
                print("    (empty config)")
            p_tags = p.get("tags", [])
            if p_tags:
                print(f"    tags: {', '.join(t['key']+'='+t['value'] for t in p_tags)}")
    else:
        print("Presets: (none)")

    # Resources with config
    print()
    modes = pipe.get("modes", [])
    for mode in modes:
        resources = mode.get("resources", [])
        configurable = []
        for res in resources:
            cf = res.get("configField", {})
            ct = cf.get("configType", {}) if cf else {}
            fields = ct.get("fields", [])
            if fields:
                configurable.append((res, fields))

        if configurable:
            print("Configurable resources:")
            for res, fields in configurable:
                desc = res.get("description", "")
                print(f"  {res['name']}: {desc[:80]}")
                for f in fields:
                    req_mark = "*" if f["isRequired"] else " "
                    default = f.get("defaultValueAsJson", "")
                    f_desc = f.get("description", "") or ""
                    print(f"    {req_mark} {f['name']}: {f['configType']['key']}"
                          + (f" = {default}" if default else "")
                          + (f"  # {f_desc[:60]}" if f_desc else ""))

    # Output as JSON for machine consumption
    print()
    print("--- JSON ---")
    out = {
        "location": location,
        "repository": repository,
        "job": pipe["name"],
        "presets": [{"name": p["name"], "runConfigYaml": p.get("runConfigYaml", "")} for p in presets],
        "tags": {t["key"]: t["value"] for t in tags},
    }
    print(json.dumps(out))


def cmd_launch(location, job_name, repository="__repository__",
               preset=None, run_config=None):
    """Launch a job with optional preset or run config."""
    # Build mutation
    params_parts = [
        'selector: {'
        f'repositoryLocationName: "{location}" '
        f'repositoryName: "{repository}" '
        f'jobName: "{job_name}"'
        '}'
    ]

    if preset:
        params_parts.append(f'preset: "{preset}"')
    elif run_config:
        # run_config is a JSON string that needs to be escaped for GraphQL string literal
        # Escape backslashes and double quotes
        escaped = run_config.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        params_parts.append(f'runConfigData: "{escaped}"')

    params = ", ".join(params_parts)

    r = gql(
        """mutation LaunchJob {
        launchRun(executionParams: {%s}) {
            __typename
            ... on LaunchRunSuccess {
                run { runId status }
            }
            ... on RunConfigValidationInvalid {
                errors { message reason }
            }
            ... on PythonError { message stack }
            ... on UnauthorizedError { message }
            ... on RunConflict { message }
            ... on InvalidStepError { invalidStepKey }
            ... on InvalidOutputError { stepKey invalidOutputName }
        }
    }"""
        % params
    )

    result = r["data"]["launchRun"]
    typename = result["__typename"]
    if typename == "LaunchRunSuccess":
        run = result["run"]
        print(f"Launched: {run['runId']} (status: {run['status']})")
    elif typename == "RunConfigValidationInvalid":
        print("Config validation failed:", file=sys.stderr)
        for err in result.get("errors", []):
            print(f"  - {err['message']}", file=sys.stderr)
        sys.exit(1)
    else:
        msg = result.get("message", "") or json.dumps(result)
        print(f"Failed ({typename}): {msg}", file=sys.stderr)
        sys.exit(1)


def cmd_reexecute(parent_run_id, strategy="FROM_FAILURE"):
    """Re-execute a run from failure or all steps."""
    r = gql(
        """mutation Reexecute {
        launchRunReexecution(
            reexecutionParams: {
                parentRunId: "%s"
                strategy: %s
            }
        ) {
            __typename
            ... on LaunchRunSuccess { run { runId status } }
            ... on RunConfigValidationInvalid { errors { message } }
            ... on PythonError { message stack }
            ... on RunConflict { message }
            ... on UnauthorizedError { message }
        }
    }"""
        % (parent_run_id, strategy)
    )

    result = r["data"]["launchRunReexecution"]
    typename = result["__typename"]
    if typename == "LaunchRunSuccess":
        run = result["run"]
        print(f"Re-executed: {run['runId']} (status: {run['status']})")
        print(f"Strategy:    {strategy}")
        print(f"Parent run:  {parent_run_id}")
    elif typename == "RunConfigValidationInvalid":
        print("Config validation failed:", file=sys.stderr)
        for err in result.get("errors", []):
            print(f"  - {err['message']}", file=sys.stderr)
        sys.exit(1)
    else:
        msg = result.get("message", "") or json.dumps(result)
        print(f"Failed ({typename}): {msg}", file=sys.stderr)
        sys.exit(1)


def cmd_terminate(run_id, force=False):
    """Terminate a running job."""
    policy = "MARK_AS_CANCELED_IMMEDIATELY" if force else "SAFE_TERMINATE"
    r = gql(
        """mutation Terminate {
        terminateRun(runId: "%s", terminatePolicy: %s) {
            __typename
            ... on TerminateRunSuccess { run { runId status } }
            ... on TerminateRunFailure { message run { runId status } }
            ... on RunNotFoundError { message }
            ... on UnauthorizedError { message }
            ... on PythonError { message }
        }
    }"""
        % (run_id, policy)
    )

    result = r["data"]["terminateRun"]
    typename = result["__typename"]
    if typename == "TerminateRunSuccess":
        run = result["run"]
        print(f"Terminated: {run['runId']} (status: {run['status']})")
        print(f"Policy:     {policy}")
    else:
        msg = result.get("message", "") or json.dumps(result)
        print(f"Failed ({typename}): {msg}", file=sys.stderr)
        sys.exit(1)


def _resolve_schedule_location(name):
    """Find which location a schedule belongs to, return (location, repo, selectorId)."""
    r = gql(
        """query {
        workspaceOrError {
            ... on Workspace {
                locationEntries {
                    name
                    locationOrLoadError {
                        ... on RepositoryLocation {
                            repositories {
                                name
                                schedules {
                                    name
                                    scheduleState { selectorId status }
                                }
                            }
                        }
                    }
                }
            }
        }
    }"""
    )
    entries = r["data"]["workspaceOrError"]["locationEntries"]
    matches = []
    name_lower = name.lower()
    for loc in entries:
        loe = loc.get("locationOrLoadError", {})
        for repo in loe.get("repositories", []):
            for s in repo.get("schedules", []):
                if s["name"].lower() == name_lower:
                    state = s["scheduleState"]
                    matches.append((loc["name"], repo["name"], s["name"], state["selectorId"], state["status"]))
    return matches


def _resolve_sensor_location(name):
    """Find which location a sensor belongs to, return (location, repo, selectorId)."""
    r = gql(
        """query {
        workspaceOrError {
            ... on Workspace {
                locationEntries {
                    name
                    locationOrLoadError {
                        ... on RepositoryLocation {
                            repositories {
                                name
                                sensors {
                                    name
                                    sensorState { selectorId status }
                                }
                            }
                        }
                    }
                }
            }
        }
    }"""
    )
    entries = r["data"]["workspaceOrError"]["locationEntries"]
    matches = []
    name_lower = name.lower()
    for loc in entries:
        loe = loc.get("locationOrLoadError", {})
        for repo in loe.get("repositories", []):
            for s in repo.get("sensors", []):
                if s["name"].lower() == name_lower:
                    state = s["sensorState"]
                    matches.append((loc["name"], repo["name"], s["name"], state["selectorId"], state["status"]))
    return matches


def cmd_schedule_toggle(name, action, location=None):
    """Start or stop a schedule."""
    matches = _resolve_schedule_location(name)
    if not matches:
        print(f"Schedule '{name}' not found.", file=sys.stderr)
        sys.exit(1)
    if len(matches) > 1 and not location:
        locs = ", ".join(m[0] for m in matches)
        print(f"Schedule '{name}' found in multiple locations: {locs}", file=sys.stderr)
        print("Use --location to specify.", file=sys.stderr)
        sys.exit(1)
    if location:
        matches = [m for m in matches if m[0] == location]
        if not matches:
            print(f"Schedule '{name}' not found in location '{location}'.", file=sys.stderr)
            sys.exit(1)

    loc_name, repo_name, sched_name, selector_id, current_status = matches[0]

    if action == "start":
        if current_status == "RUNNING":
            print(f"Schedule '{sched_name}' is already running.")
            return
        r = gql(
            """mutation StartSchedule {
            startSchedule(scheduleSelector: {
                repositoryLocationName: "%s"
                repositoryName: "%s"
                scheduleName: "%s"
            }) {
                __typename
                ... on ScheduleStateResult { scheduleState { status name } }
                ... on ScheduleNotFoundError { message }
                ... on UnauthorizedError { message }
                ... on PythonError { message }
            }
        }"""
            % (loc_name, repo_name, sched_name)
        )
        result = r["data"]["startSchedule"]
    else:  # stop
        if current_status == "STOPPED":
            print(f"Schedule '{sched_name}' is already stopped.")
            return
        r = gql(
            """mutation StopSchedule {
            stopRunningSchedule(scheduleSelectorId: "%s") {
                __typename
                ... on ScheduleStateResult { scheduleState { status name } }
                ... on ScheduleNotFoundError { message }
                ... on UnauthorizedError { message }
                ... on PythonError { message }
            }
        }"""
            % selector_id
        )
        result = r["data"]["stopRunningSchedule"]

    typename = result["__typename"]
    if typename == "ScheduleStateResult":
        state = result["scheduleState"]
        print(f"Schedule: {loc_name}/{state['name']}")
        print(f"Status:   {state['status']}")
    else:
        msg = result.get("message", "") or json.dumps(result)
        print(f"Failed ({typename}): {msg}", file=sys.stderr)
        sys.exit(1)


def cmd_sensor_toggle(name, action, location=None):
    """Start or stop a sensor."""
    matches = _resolve_sensor_location(name)
    if not matches:
        print(f"Sensor '{name}' not found.", file=sys.stderr)
        sys.exit(1)
    if len(matches) > 1 and not location:
        locs = ", ".join(m[0] for m in matches)
        print(f"Sensor '{name}' found in multiple locations: {locs}", file=sys.stderr)
        print("Use --location to specify.", file=sys.stderr)
        sys.exit(1)
    if location:
        matches = [m for m in matches if m[0] == location]
        if not matches:
            print(f"Sensor '{name}' not found in location '{location}'.", file=sys.stderr)
            sys.exit(1)

    loc_name, repo_name, sensor_name, selector_id, current_status = matches[0]

    if action == "start":
        if current_status == "RUNNING":
            print(f"Sensor '{sensor_name}' is already running.")
            return
        r = gql(
            """mutation StartSensor {
            startSensor(sensorSelector: {
                repositoryLocationName: "%s"
                repositoryName: "%s"
                sensorName: "%s"
            }) {
                __typename
                ... on Sensor { name sensorState { status } }
                ... on SensorNotFoundError { message }
                ... on UnauthorizedError { message }
                ... on PythonError { message }
            }
        }"""
            % (loc_name, repo_name, sensor_name)
        )
        result = r["data"]["startSensor"]
        typename = result["__typename"]
        if typename == "Sensor":
            print(f"Sensor:   {loc_name}/{result['name']}")
            print(f"Status:   {result['sensorState']['status']}")
        else:
            msg = result.get("message", "") or json.dumps(result)
            print(f"Failed ({typename}): {msg}", file=sys.stderr)
            sys.exit(1)
    else:  # stop
        if current_status == "STOPPED":
            print(f"Sensor '{sensor_name}' is already stopped.")
            return
        r = gql(
            """mutation StopSensor {
            stopSensor(jobSelectorId: "%s") {
                __typename
                ... on StopSensorMutationResult { instigationState { status name } }
                ... on UnauthorizedError { message }
                ... on PythonError { message }
            }
        }"""
            % selector_id
        )
        result = r["data"]["stopSensor"]
        typename = result["__typename"]
        if typename == "StopSensorMutationResult":
            state = result["instigationState"]
            print(f"Sensor:   {loc_name}/{state['name']}")
            print(f"Status:   {state['status']}")
        else:
            msg = result.get("message", "") or json.dumps(result)
            print(f"Failed ({typename}): {msg}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    # Parse --step filter from args
    step_filter = None
    for i, arg in enumerate(sys.argv):
        if arg == "--step" and i + 1 < len(sys.argv):
            step_filter = sys.argv[i + 1]

    if cmd == "job-runs":
        job_name = sys.argv[2]
        limit = 10
        status_filter = None
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--limit" and i + 1 < len(sys.argv):
                limit = int(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--status" and i + 1 < len(sys.argv):
                status_filter = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        cmd_job_runs(job_name, limit, status_filter)
    elif cmd == "run-detail":
        run_id = sys.argv[2]
        log_limit = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        cmd_run_detail(run_id, log_limit, step_filter)
    elif cmd == "run-logs":
        run_id = sys.argv[2]
        log_limit = int(sys.argv[3]) if len(sys.argv) > 3 else 200
        failures_only = "--failures-only" in sys.argv
        cmd_run_logs(run_id, log_limit, failures_only, step_filter)
    elif cmd == "job-info":
        location = sys.argv[2]
        job_name = sys.argv[3]
        repository = sys.argv[4] if len(sys.argv) > 4 else "__repository__"
        cmd_job_info(location, job_name, repository)
    elif cmd == "launch":
        location = sys.argv[2]
        job_name = sys.argv[3]
        repository = sys.argv[4] if len(sys.argv) > 4 else "__repository__"
        preset = None
        run_config = None
        i = 5
        while i < len(sys.argv):
            if sys.argv[i] == "--preset" and i + 1 < len(sys.argv):
                preset = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--run-config" and i + 1 < len(sys.argv):
                run_config = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        cmd_launch(location, job_name, repository, preset, run_config)
    elif cmd == "reexecute":
        parent_run_id = sys.argv[2]
        strategy = sys.argv[3] if len(sys.argv) > 3 else "FROM_FAILURE"
        cmd_reexecute(parent_run_id, strategy)
    elif cmd == "terminate":
        run_id = sys.argv[2]
        force = "--force" in sys.argv
        cmd_terminate(run_id, force)
    elif cmd == "schedule":
        action = sys.argv[2]  # start or stop
        name = sys.argv[3]
        location = None
        for i, arg in enumerate(sys.argv):
            if arg == "--location" and i + 1 < len(sys.argv):
                location = sys.argv[i + 1]
        cmd_schedule_toggle(name, action, location)
    elif cmd == "sensor":
        action = sys.argv[2]  # start or stop
        name = sys.argv[3]
        location = None
        for i, arg in enumerate(sys.argv):
            if arg == "--location" and i + 1 < len(sys.argv):
                location = sys.argv[i + 1]
        cmd_sensor_toggle(name, action, location)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
