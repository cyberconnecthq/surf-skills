#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["langfuse>=2.0,<4.0"]
# ///
"""
Fetch Langfuse trace data and save to local files for analysis.

Usage:
    uv run fetch_trace.py <trace_id> [--force] [--fast]     # Fetch a single trace
    uv run fetch_trace.py --session <session_id> [--fast]   # Fetch all traces in a session
    uv run fetch_trace.py --list                            # List cached traces
    uv run fetch_trace.py --clean [days]                    # Delete traces older than N days (default: 7)
    uv run fetch_trace.py --clean-all                       # Delete all cached traces

Config priority: env vars > ~/.config/langfuse/config.json > AWS Secrets Manager.

Output structure (single trace):
    /tmp/trace_analysis/<trace_id>/
    ├── trace_meta.json          # Trace metadata (id, name, user_id, timestamps)
    ├── trace_input.txt          # Full trace input
    ├── trace_output.txt         # Full trace output
    ├── observations_summary.txt # Quick overview of all observations
    ├── call_tree.txt            # Hierarchical call tree visualization
    ├── tools_only.txt           # Just tool calls with inputs/outputs
    ├── llm_only.txt             # Just LLM generations with outputs
    ├── cost_summary.txt         # Token usage and cost breakdown
    ├── observations/            # (skipped with --fast)
    │   ├── 001_<name>.json      # Full observation data
    │   ├── 001_<name>_input.txt # Observation input (for grep)
    │   ├── 001_<name>_output.txt# Observation output (for grep)
    │   └── ...
    └── all_outputs.txt          # Concatenated outputs for searching

Output structure (session):
    /tmp/trace_analysis/sessions/<session_id>/
    ├── session_meta.json        # Session metadata (traces list, user queries)
    ├── session_timeline.txt     # Chronological trace list with inputs
    ├── session_cost_summary.txt # Aggregated costs across all traces
    └── traces/
        ├── 01_<trace_id>/       # Individual trace folders (numbered by order)
        │   └── ... (same as single trace)
        └── ...
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# -- Proxy sanitization (must run before any HTTP library is imported) --------
# SOCKS proxy: httpx crashes without the socksio package — always remove.
# HTTP proxy: internal hosts (*.ask.surf) are reachable directly — proxying
# causes timeouts or SSL errors.

_INTERNAL_HOSTS = (".ask.surf", ".svc.cluster.local", "localhost", "127.0.0.1")

# Always nuke SOCKS proxy
for _var in ("all_proxy", "ALL_PROXY"):
    os.environ.pop(_var, None)

# Pre-load LANGFUSE_HOST from config file to decide on HTTP proxy
_CONFIG_PATH = Path.home() / ".config" / "langfuse" / "config.json"
_host_hint = os.environ.get("LANGFUSE_HOST", "")
if not _host_hint and _CONFIG_PATH.exists():
    try:
        _host_hint = json.loads(_CONFIG_PATH.read_text()).get("langfuse_host", "")
    except Exception:
        pass
if any(h in _host_hint for h in _INTERNAL_HOSTS):
    for _var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
        os.environ.pop(_var, None)

del _var, _host_hint  # cleanup module namespace
# -----------------------------------------------------------------------------

from langfuse import Langfuse

_langfuse = None


def _load_from_aws():
    """Load Langfuse credentials from AWS Secrets Manager via AWS CLI.

    Only sets env vars that are not already set (lowest priority source).
    """
    try:
        result = subprocess.run(
            ["aws", "secretsmanager", "get-secret-value",
             "--secret-id", "langfuse/surf-ai/bot",
             "--query", "SecretString", "--output", "text"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return
        secret = json.loads(result.stdout)
        key_map = {
            "public_key": "LANGFUSE_PUBLIC_KEY",
            "secret_key": "LANGFUSE_SECRET_KEY",
            "base_url": "LANGFUSE_HOST",
        }
        for secret_key, env_var in key_map.items():
            if secret_key in secret and env_var not in os.environ:
                os.environ[env_var] = secret[secret_key]
    except Exception:
        pass


def _load_config():
    """Load Langfuse credentials. Priority: env vars > config file > AWS Secrets Manager.

    Config file takes precedence over AWS because it represents explicit local
    intent, while AWS secrets may be stale (e.g. after a cloud-to-self-hosted migration).
    """
    _REQUIRED_KEYS = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST")

    # 1. If all env vars already set, nothing to do
    if all(k in os.environ for k in _REQUIRED_KEYS):
        return

    # 2. Try config file (local, explicit user config)
    if _CONFIG_PATH.exists():
        try:
            config = json.loads(_CONFIG_PATH.read_text())
            for key in _REQUIRED_KEYS:
                if key not in os.environ and key.lower() in config:
                    os.environ[key] = config[key.lower()]
        except (json.JSONDecodeError, KeyError):
            pass
        # If config file provided enough keys, skip AWS
        if all(k in os.environ for k in _REQUIRED_KEYS[:2]):
            return

    # 3. AWS Secrets Manager (auto-discovered, may be stale after migration)
    _load_from_aws()


def _get_client():
    global _langfuse
    if _langfuse is None:
        _load_config()
        _langfuse = Langfuse()
    return _langfuse


def get_trace_details(trace_id: str):
    """Fetch a single trace by ID."""
    return _get_client().api.trace.get(trace_id)


def get_observations_from_trace(trace_id: str, max_observations: int = 500):
    """Fetch all observations for a trace, paginating if needed."""
    client = _get_client()
    all_obs = []
    page = 1
    while len(all_obs) < max_observations:
        batch_limit = min(100, max_observations - len(all_obs))
        result = client.api.observations.get_many(trace_id=trace_id, limit=batch_limit, page=page)
        all_obs.extend(result.data)
        if len(result.data) < batch_limit:
            break
        page += 1
    return all_obs


def fetch_traces_by_session(session_id: str, limit: int = 100):
    """Fetch all traces in a session."""
    return _get_client().api.trace.list(session_id=session_id, limit=limit).data


def sanitize_filename(name: str, max_length: int = 50) -> str:
    """Convert observation name to safe filename."""
    if not name:
        return "unnamed"
    # Remove special characters, keep alphanumeric and some safe chars
    safe = re.sub(r"[^\w\s\-_]", "", name)
    safe = re.sub(r"\s+", "_", safe)
    return safe[:max_length]


def serialize_value(value) -> str:
    """Convert any value to string for text file."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, ensure_ascii=False, default=str)
    return str(value)


def datetime_serializer(obj):
    """JSON serializer for datetime objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def build_call_tree(observations: list) -> str:
    """Build a hierarchical call tree from observations."""
    # Create lookup maps
    id_to_obs = {obs.id: obs for obs in observations}
    children_map = {}  # parent_id -> list of children

    for obs in observations:
        parent_id = obs.parent_observation_id
        if parent_id not in children_map:
            children_map[parent_id] = []
        children_map[parent_id].append(obs)

    # Sort children by start_time
    for parent_id in children_map:
        children_map[parent_id].sort(key=lambda x: x.start_time or datetime.min)

    lines = ["CALL TREE", "=" * 80, ""]

    def render_node(obs, depth=0):
        indent = "    " * depth
        prefix = "├── " if depth > 0 else ""

        # Calculate duration
        duration_str = ""
        if obs.start_time and obs.end_time:
            duration_ms = (obs.end_time - obs.start_time).total_seconds() * 1000
            if duration_ms < 1000:
                duration_str = f"({duration_ms:.0f}ms)"
            else:
                duration_str = f"({duration_ms/1000:.2f}s)"

        type_label = obs.type or "SPAN"
        model_info = f" [{obs.model}]" if obs.model else ""

        lines.append(f"{indent}{prefix}{type_label}: {obs.name}{model_info} {duration_str}")

        # Render children
        if obs.id in children_map:
            for child in children_map[obs.id]:
                render_node(child, depth + 1)

    # Find root nodes (no parent)
    roots = children_map.get(None, [])
    for root in roots:
        render_node(root, 0)

    return "\n".join(lines)


def build_tools_summary(observations: list) -> str:
    """Build a summary of just tool calls."""
    lines = ["TOOL CALLS SUMMARY", "=" * 80, ""]

    tool_obs = [obs for obs in observations if obs.type == "TOOL" or (obs.type == "SPAN" and obs.name not in ["AskFast", "ask_reporter", "ask_fast_coordinator", "ask_fast_retriever", "__start__", "Toolcall", "build_retrieval_context", "language_detect"])]

    for idx, obs in enumerate(tool_obs, 1):
        duration_str = ""
        if obs.start_time and obs.end_time:
            duration_ms = (obs.end_time - obs.start_time).total_seconds() * 1000
            duration_str = f"{duration_ms:.0f}ms" if duration_ms < 1000 else f"{duration_ms/1000:.2f}s"

        lines.append(f"[{idx}] {obs.name} ({duration_str})")
        lines.append(f"    ID: {obs.id}")

        # Input summary
        input_str = serialize_value(obs.input)
        if len(input_str) > 500:
            input_str = input_str[:500] + "..."
        lines.append(f"    INPUT: {input_str}")

        # Output summary
        output_str = serialize_value(obs.output)
        if len(output_str) > 500:
            output_str = output_str[:500] + "..."
        lines.append(f"    OUTPUT: {output_str}")
        lines.append("")

    return "\n".join(lines)


def build_llm_summary(observations: list) -> str:
    """Build a summary of just LLM generations."""
    lines = ["LLM GENERATIONS SUMMARY", "=" * 80, ""]

    llm_obs = [obs for obs in observations if obs.type == "GENERATION"]

    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0

    for idx, obs in enumerate(llm_obs, 1):
        duration_str = ""
        if obs.start_time and obs.end_time:
            duration_ms = (obs.end_time - obs.start_time).total_seconds() * 1000
            duration_str = f"{duration_ms:.0f}ms" if duration_ms < 1000 else f"{duration_ms/1000:.2f}s"

        lines.append(f"[{idx}] {obs.name} - {obs.model} ({duration_str})")
        lines.append(f"    ID: {obs.id}")

        # Token usage
        if obs.usage:
            input_tokens = getattr(obs.usage, "input", 0) or 0
            output_tokens = getattr(obs.usage, "output", 0) or 0
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens
            lines.append(f"    Tokens: {input_tokens} in / {output_tokens} out")

        if obs.calculated_total_cost:
            total_cost += obs.calculated_total_cost
            lines.append(f"    Cost: ${obs.calculated_total_cost:.6f}")

        # Output summary (what did the LLM decide/say)
        output_str = serialize_value(obs.output)

        # Try to extract just the content/text
        try:
            if isinstance(obs.output, dict):
                content = obs.output.get("content", "")
                if isinstance(content, list):
                    text_parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
                    content = " ".join(text_parts)
                output_str = content if content else output_str
        except Exception:
            pass

        if len(output_str) > 800:
            output_str = output_str[:800] + "..."
        lines.append(f"    OUTPUT: {output_str}")
        lines.append("")

    lines.append("=" * 80)
    lines.append(f"TOTAL: {len(llm_obs)} generations")
    lines.append(f"TOTAL TOKENS: {total_input_tokens} input / {total_output_tokens} output")
    lines.append(f"TOTAL COST: ${total_cost:.6f}")

    return "\n".join(lines)


def extract_key_values(observations: list) -> str:
    """Extract searchable key values (numbers, addresses, URLs) from all observations.

    This creates a quick-reference file so Claude can find data sources
    without grepping through large files.
    """
    lines = ["KEY VALUES INDEX", "=" * 80, ""]
    lines.append("This file indexes important values for quick searching.")
    lines.append("Format: VALUE | OBSERVATION # | OBSERVATION NAME | IN/OUT")
    lines.append("")

    # Patterns to extract
    import re
    patterns = {
        "numbers": r'\$[\d,]+\.?\d*[MBKmk]?|\d{1,3}(?:,\d{3})*(?:\.\d+)?%?(?:\s*(?:million|billion|M|B|K))?',
        "addresses": r'0x[a-fA-F0-9]{8,64}',
        "urls": r'https?://[^\s\"\'\]>]+',
    }

    seen_values = set()  # Avoid duplicates

    for idx, obs in enumerate(observations, 1):
        obs_name = obs.name or "unnamed"

        for field, location in [("input", "INPUT"), ("output", "OUTPUT")]:
            content = serialize_value(getattr(obs, field, None))
            if not content:
                continue

            # Extract numbers (prices, volumes, percentages)
            for match in re.finditer(patterns["numbers"], content):
                value = match.group().strip()
                if len(value) > 3 and value not in seen_values:  # Skip tiny numbers
                    seen_values.add(value)
                    lines.append(f"{value} | #{idx:03d} | {obs_name} | {location}")

            # Extract addresses (first 5 only per observation to avoid spam)
            addr_count = 0
            for match in re.finditer(patterns["addresses"], content):
                if addr_count >= 5:
                    break
                value = match.group()
                key = f"{value[:20]}|{idx}"  # Dedupe by prefix + obs
                if key not in seen_values:
                    seen_values.add(key)
                    # Truncate long addresses for display
                    display = f"{value[:10]}...{value[-6:]}" if len(value) > 20 else value
                    lines.append(f"{display} | #{idx:03d} | {obs_name} | {location}")
                    addr_count += 1

    lines.append("")
    lines.append(f"Total indexed values: {len(seen_values)}")
    return "\n".join(lines)


def build_cost_summary(observations: list) -> str:
    """Build a cost and token usage summary."""
    lines = ["COST & TOKEN USAGE SUMMARY", "=" * 80, ""]

    llm_obs = [obs for obs in observations if obs.type == "GENERATION"]

    model_stats = {}

    for obs in llm_obs:
        model = obs.model or "unknown"
        if model not in model_stats:
            model_stats[model] = {
                "count": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0,
                "total_duration_ms": 0
            }

        model_stats[model]["count"] += 1

        if obs.usage:
            input_tokens = getattr(obs.usage, "input", 0) or 0
            output_tokens = getattr(obs.usage, "output", 0) or 0
            model_stats[model]["input_tokens"] += input_tokens
            model_stats[model]["output_tokens"] += output_tokens

        if obs.calculated_total_cost:
            model_stats[model]["cost"] += obs.calculated_total_cost

        if obs.start_time and obs.end_time:
            duration_ms = (obs.end_time - obs.start_time).total_seconds() * 1000
            model_stats[model]["total_duration_ms"] += duration_ms

    lines.append("BY MODEL:")
    lines.append("-" * 60)

    total_cost = 0.0
    total_input = 0
    total_output = 0

    for model, stats in sorted(model_stats.items()):
        lines.append(f"\n{model}:")
        lines.append(f"  Calls: {stats['count']}")
        lines.append(f"  Tokens: {stats['input_tokens']:,} input / {stats['output_tokens']:,} output")
        lines.append(f"  Cost: ${stats['cost']:.6f}")
        lines.append(f"  Total Time: {stats['total_duration_ms']/1000:.2f}s")

        total_cost += stats["cost"]
        total_input += stats["input_tokens"]
        total_output += stats["output_tokens"]

    lines.append("")
    lines.append("=" * 60)
    lines.append(f"GRAND TOTAL:")
    lines.append(f"  LLM Calls: {len(llm_obs)}")
    lines.append(f"  Input Tokens: {total_input:,}")
    lines.append(f"  Output Tokens: {total_output:,}")
    lines.append(f"  Total Cost: ${total_cost:.6f}")

    return "\n".join(lines)


def fetch_and_save_trace(trace_id: str, output_dir: str = None, force: bool = False, skip_obs_files: bool = False) -> str:
    """
    Fetch trace data from Langfuse and save to local files.

    Args:
        trace_id: The Langfuse trace ID
        output_dir: Custom output directory (default: /tmp/trace_analysis/<id>)
        force: Force re-fetch even if cached
        skip_obs_files: Skip writing individual observation files (faster)

    Returns the output directory path.
    """
    # Default output directory
    if output_dir is None:
        output_dir = f"/tmp/trace_analysis/{trace_id[:16]}"

    output_path = Path(output_dir)
    obs_path = output_path / "observations"

    # Check if already cached (skip re-fetch unless forced)
    if output_path.exists() and (output_path / "trace_meta.json").exists() and not force:
        print(f"Using cached trace: {output_path}")
        print("(use --force to re-fetch)")
        return str(output_path)

    # Clean and create directories
    if output_path.exists():
        import shutil
        shutil.rmtree(output_path)

    output_path.mkdir(parents=True, exist_ok=True)
    if not skip_obs_files:
        obs_path.mkdir(parents=True, exist_ok=True)

    print(f"Fetching trace: {trace_id}")

    # Fetch trace metadata
    trace = get_trace_details(trace_id)
    if not trace:
        print(f"ERROR: Could not find trace {trace_id}")
        sys.exit(1)

    # Save trace metadata
    trace_meta = {
        "id": trace.id,
        "name": trace.name,
        "user_id": trace.user_id,
        "session_id": trace.session_id,
        "timestamp": trace.timestamp,
        "tags": trace.tags,
        "metadata": trace.metadata,
    }

    with open(output_path / "trace_meta.json", "w") as f:
        json.dump(trace_meta, f, indent=2, default=datetime_serializer)

    # Save trace input/output as separate text files (for easy grepping)
    with open(output_path / "trace_input.txt", "w") as f:
        f.write(serialize_value(trace.input))

    with open(output_path / "trace_output.txt", "w") as f:
        f.write(serialize_value(trace.output))

    print(f"Fetching observations...")

    # Fetch all observations
    observations = get_observations_from_trace(trace_id, max_observations=500)
    print(f"Found {len(observations)} observations")

    # Build summary and save individual observations
    summary_lines = []
    summary_lines.append(f"TRACE: {trace_id}")
    summary_lines.append(f"NAME: {trace.name}")
    summary_lines.append(f"TIMESTAMP: {trace.timestamp}")
    summary_lines.append(f"OBSERVATIONS: {len(observations)}")
    summary_lines.append("")
    summary_lines.append("=" * 80)
    summary_lines.append("OBSERVATION INDEX")
    summary_lines.append("=" * 80)
    summary_lines.append("")

    all_outputs = []  # For concatenated search file

    for idx, obs in enumerate(observations, 1):
        safe_name = sanitize_filename(obs.name)
        prefix = f"{idx:03d}_{safe_name}"

        # Calculate duration
        duration_str = ""
        if obs.start_time and obs.end_time:
            duration_ms = (obs.end_time - obs.start_time).total_seconds() * 1000
            if duration_ms < 1000:
                duration_str = f"{duration_ms:.0f}ms"
            else:
                duration_str = f"{duration_ms/1000:.2f}s"

        # Add to summary
        summary_lines.append(f"[{idx:03d}] {obs.type or 'UNKNOWN'}: {obs.name}")
        summary_lines.append(f"      ID: {obs.id}")
        summary_lines.append(f"      Model: {obs.model or 'N/A'}")
        summary_lines.append(f"      Duration: {duration_str or 'N/A'}")
        summary_lines.append(f"      Files: observations/{prefix}_*.txt")
        if obs.parent_observation_id:
            summary_lines.append(f"      Parent: {obs.parent_observation_id}")
        summary_lines.append("")

        # Save full observation as JSON
        obs_data = {
            "index": idx,
            "id": obs.id,
            "name": obs.name,
            "type": obs.type,
            "model": obs.model,
            "trace_id": obs.trace_id,
            "parent_observation_id": obs.parent_observation_id,
            "start_time": obs.start_time,
            "end_time": obs.end_time,
            "duration_ms": duration_str,
            "level": obs.level,
            "usage": obs.usage,
            "calculated_total_cost": obs.calculated_total_cost,
            "metadata": obs.metadata,
            "input": obs.input,
            "output": obs.output,
        }

        # Save individual observation files (skip if --fast mode)
        input_content = serialize_value(obs.input)
        output_content = serialize_value(obs.output)

        if not skip_obs_files:
            with open(obs_path / f"{prefix}.json", "w") as f:
                json.dump(obs_data, f, indent=2, default=datetime_serializer, ensure_ascii=False)

            with open(obs_path / f"{prefix}_input.txt", "w") as f:
                f.write(f"### OBSERVATION {idx}: {obs.name} ###\n")
                f.write(f"### TYPE: {obs.type} | MODEL: {obs.model} | ID: {obs.id} ###\n")
                f.write(f"### INPUT ###\n\n")
                f.write(input_content)

            with open(obs_path / f"{prefix}_output.txt", "w") as f:
                f.write(f"### OBSERVATION {idx}: {obs.name} ###\n")
                f.write(f"### TYPE: {obs.type} | MODEL: {obs.model} | ID: {obs.id} ###\n")
                f.write(f"### OUTPUT ###\n\n")
                f.write(output_content)

        # Add to concatenated outputs file
        all_outputs.append(f"\n{'='*80}")
        all_outputs.append(f"OBSERVATION {idx}: {obs.name}")
        all_outputs.append(f"TYPE: {obs.type} | MODEL: {obs.model}")
        all_outputs.append(f"ID: {obs.id}")
        all_outputs.append(f"{'='*80}\n")
        all_outputs.append("--- INPUT ---")
        all_outputs.append(input_content[:5000] if len(input_content) > 5000 else input_content)
        all_outputs.append("\n--- OUTPUT ---")
        all_outputs.append(output_content[:5000] if len(output_content) > 5000 else output_content)

    # Save summary
    with open(output_path / "observations_summary.txt", "w") as f:
        f.write("\n".join(summary_lines))

    # Save concatenated outputs for quick searching
    with open(output_path / "all_outputs.txt", "w") as f:
        f.write("\n".join(all_outputs))

    # Save call tree visualization
    with open(output_path / "call_tree.txt", "w") as f:
        f.write(build_call_tree(observations))

    # Save tools-only summary
    with open(output_path / "tools_only.txt", "w") as f:
        f.write(build_tools_summary(observations))

    # Save LLM-only summary
    with open(output_path / "llm_only.txt", "w") as f:
        f.write(build_llm_summary(observations))

    # Save cost summary
    with open(output_path / "cost_summary.txt", "w") as f:
        f.write(build_cost_summary(observations))

    # Save key values index (for quick lookups)
    with open(output_path / "key_values.txt", "w") as f:
        f.write(extract_key_values(observations))

    # Print results
    print(f"\nTrace data saved to: {output_path}")
    print(f"\nFiles created:")
    print(f"  - trace_meta.json          (trace metadata)")
    print(f"  - trace_input.txt          (trace input)")
    print(f"  - trace_output.txt         (trace output)")
    print(f"  - observations_summary.txt (overview of all {len(observations)} observations)")
    print(f"  - call_tree.txt            (hierarchical call tree)")
    print(f"  - tools_only.txt           (tool calls with inputs/outputs)")
    print(f"  - llm_only.txt             (LLM generations with outputs)")
    print(f"  - cost_summary.txt         (token usage and costs)")
    print(f"  - key_values.txt           (indexed numbers, addresses for quick lookup)")
    print(f"  - all_outputs.txt          (full text for grep)")
    if not skip_obs_files:
        print(f"  - observations/            ({len(observations)} observations, 3 files each)")
    else:
        print(f"  (observations/ skipped with --fast)")

    return str(output_path)


def list_cached_traces() -> None:
    """List all cached traces with their sizes and ages."""
    base_dir = Path("/tmp/trace_analysis")

    if not base_dir.exists():
        print("No cached traces found.")
        return

    traces = list(base_dir.iterdir())
    if not traces:
        print("No cached traces found.")
        return

    print("CACHED TRACES")
    print("=" * 80)
    print(f"{'Trace ID':<20} {'Size':>10} {'Age':>12} {'Name':<30}")
    print("-" * 80)

    total_size = 0

    for trace_dir in sorted(traces, key=lambda x: x.stat().st_mtime, reverse=True):
        if not trace_dir.is_dir():
            continue

        # Calculate directory size
        size = sum(f.stat().st_size for f in trace_dir.rglob("*") if f.is_file())
        total_size += size

        # Get age
        mtime = datetime.fromtimestamp(trace_dir.stat().st_mtime)
        age = datetime.now() - mtime
        if age.days > 0:
            age_str = f"{age.days}d ago"
        elif age.seconds > 3600:
            age_str = f"{age.seconds // 3600}h ago"
        else:
            age_str = f"{age.seconds // 60}m ago"

        # Get trace name from meta
        name = ""
        meta_file = trace_dir / "trace_meta.json"
        if meta_file.exists():
            try:
                with open(meta_file) as f:
                    meta = json.load(f)
                    name = meta.get("name", "")[:30]
            except Exception:
                pass

        # Format size
        if size > 1024 * 1024:
            size_str = f"{size / (1024*1024):.1f}MB"
        else:
            size_str = f"{size / 1024:.0f}KB"

        print(f"{trace_dir.name:<20} {size_str:>10} {age_str:>12} {name:<30}")

    print("-" * 80)
    if total_size > 1024 * 1024:
        print(f"Total: {len(traces)} traces, {total_size / (1024*1024):.1f}MB")
    else:
        print(f"Total: {len(traces)} traces, {total_size / 1024:.0f}KB")


def clean_old_traces(days: int = 7) -> None:
    """Delete traces older than N days."""
    import shutil

    base_dir = Path("/tmp/trace_analysis")

    if not base_dir.exists():
        print("No cached traces to clean.")
        return

    cutoff = datetime.now().timestamp() - (days * 24 * 3600)
    deleted = 0
    freed = 0

    for trace_dir in list(base_dir.iterdir()):
        if not trace_dir.is_dir():
            continue

        if trace_dir.stat().st_mtime < cutoff:
            size = sum(f.stat().st_size for f in trace_dir.rglob("*") if f.is_file())
            shutil.rmtree(trace_dir)
            deleted += 1
            freed += size

    if freed > 1024 * 1024:
        freed_str = f"{freed / (1024*1024):.1f}MB"
    else:
        freed_str = f"{freed / 1024:.0f}KB"

    print(f"Deleted {deleted} traces older than {days} days, freed {freed_str}")


def clean_all_traces() -> None:
    """Delete all cached traces."""
    import shutil

    base_dir = Path("/tmp/trace_analysis")

    if not base_dir.exists():
        print("No cached traces to clean.")
        return

    size = sum(f.stat().st_size for f in base_dir.rglob("*") if f.is_file())
    count = len(list(base_dir.iterdir()))

    shutil.rmtree(base_dir)

    if size > 1024 * 1024:
        size_str = f"{size / (1024*1024):.1f}MB"
    else:
        size_str = f"{size / 1024:.0f}KB"

    print(f"Deleted all {count} traces, freed {size_str}")


def fetch_and_save_session(session_id: str, force: bool = False, skip_obs_files: bool = False) -> str:
    """
    Fetch all traces in a session and save to local files.

    Args:
        session_id: The Langfuse session ID
        force: Force re-fetch even if cached
        skip_obs_files: Skip writing individual observation files (faster)

    Returns the output directory path.
    """
    import shutil

    # Output directory for session
    output_dir = f"/tmp/trace_analysis/sessions/{session_id[:16]}"
    output_path = Path(output_dir)
    traces_path = output_path / "traces"

    # Check if already cached
    if output_path.exists() and (output_path / "session_meta.json").exists() and not force:
        print(f"Using cached session: {output_path}")
        print("(use --force to re-fetch)")
        return str(output_path)

    # Clean and create directories
    if output_path.exists():
        shutil.rmtree(output_path)

    output_path.mkdir(parents=True, exist_ok=True)
    traces_path.mkdir(parents=True, exist_ok=True)

    print(f"Fetching traces for session: {session_id}")

    # Fetch all traces in session
    traces = fetch_traces_by_session(session_id, limit=100)

    if not traces:
        print(f"ERROR: No traces found for session {session_id}")
        sys.exit(1)

    print(f"Found {len(traces)} traces in session")

    # Build session metadata
    session_meta = {
        "session_id": session_id,
        "trace_count": len(traces),
        "traces": [],
        "fetched_at": datetime.now().isoformat(),
    }

    # Build session timeline
    timeline_lines = ["SESSION TIMELINE", "=" * 80, ""]
    timeline_lines.append(f"Session ID: {session_id}")
    timeline_lines.append(f"Trace Count: {len(traces)}")
    timeline_lines.append("")
    timeline_lines.append("=" * 80)
    timeline_lines.append("")

    # Aggregated cost tracking
    total_cost = 0.0
    total_input_tokens = 0
    total_output_tokens = 0
    total_llm_calls = 0
    model_stats = {}

    # Process each trace
    for idx, trace in enumerate(traces, 1):
        trace_id = trace.id
        if not trace_id:
            continue

        # Create numbered trace folder
        trace_folder = traces_path / f"{idx:02d}_{trace_id[:12]}"
        trace_folder.mkdir(parents=True, exist_ok=True)

        # Add to session meta
        user_input = ""
        if trace.input:
            if isinstance(trace.input, list) and len(trace.input) > 0:
                first_item = trace.input[0]
                if isinstance(first_item, dict):
                    user_input = first_item.get("text", str(first_item))[:200]
                else:
                    user_input = str(first_item)[:200]
            elif isinstance(trace.input, str):
                user_input = trace.input[:200]
            else:
                user_input = str(trace.input)[:200]

        session_meta["traces"].append({
            "index": idx,
            "trace_id": trace_id,
            "name": trace.name,
            "timestamp": trace.timestamp.isoformat() if trace.timestamp else None,
            "user_input": user_input,
            "folder": str(trace_folder.name),
        })

        # Add to timeline
        timestamp_str = trace.timestamp.strftime("%Y-%m-%d %H:%M:%S") if trace.timestamp else "N/A"
        timeline_lines.append(f"[{idx:02d}] {timestamp_str} - {trace.name or 'unnamed'}")
        timeline_lines.append(f"     Trace ID: {trace_id}")
        timeline_lines.append(f"     Folder: traces/{trace_folder.name}/")
        if user_input:
            # Truncate and show user input
            display_input = user_input.replace("\n", " ")[:100]
            if len(user_input) > 100:
                display_input += "..."
            timeline_lines.append(f"     Input: {display_input}")
        timeline_lines.append("")

        print(f"  [{idx}/{len(traces)}] Fetching trace: {trace_id[:16]}...")

        # Fetch and save this trace (reuse existing function logic but with custom output dir)
        fetch_and_save_trace(
            trace_id,
            output_dir=str(trace_folder),
            force=True,  # Always fetch since we're building fresh session
            skip_obs_files=skip_obs_files
        )

        # Aggregate costs from this trace
        cost_file = trace_folder / "cost_summary.txt"
        if cost_file.exists():
            with open(cost_file) as f:
                cost_content = f.read()

            # Parse cost summary
            for line in cost_content.split("\n"):
                line = line.strip()
                if line.startswith("LLM Calls:"):
                    try:
                        total_llm_calls += int(line.split(":")[1].strip())
                    except (ValueError, IndexError):
                        pass
                elif line.startswith("Input Tokens:"):
                    try:
                        total_input_tokens += int(line.split(":")[1].strip().replace(",", ""))
                    except (ValueError, IndexError):
                        pass
                elif line.startswith("Output Tokens:"):
                    try:
                        total_output_tokens += int(line.split(":")[1].strip().replace(",", ""))
                    except (ValueError, IndexError):
                        pass
                elif line.startswith("Total Cost:"):
                    try:
                        cost_str = line.split(":")[1].strip().replace("$", "")
                        total_cost += float(cost_str)
                    except (ValueError, IndexError):
                        pass

            # Parse per-model stats
            current_model = None
            for line in cost_content.split("\n"):
                line = line.strip()
                if line and not line.startswith(("BY MODEL", "-", "=", "GRAND", "LLM", "Input", "Output", "Total")):
                    if line.endswith(":") and not line.startswith("  "):
                        current_model = line[:-1]
                        if current_model not in model_stats:
                            model_stats[current_model] = {
                                "calls": 0,
                                "input_tokens": 0,
                                "output_tokens": 0,
                                "cost": 0.0,
                            }
                    elif current_model and line.startswith("Calls:"):
                        try:
                            model_stats[current_model]["calls"] += int(line.split(":")[1].strip())
                        except (ValueError, IndexError):
                            pass
                    elif current_model and line.startswith("Tokens:"):
                        try:
                            tokens_part = line.split(":")[1].strip()
                            parts = tokens_part.split("/")
                            input_tokens = int(parts[0].strip().replace(",", "").replace(" input", ""))
                            output_tokens = int(parts[1].strip().replace(",", "").replace(" output", ""))
                            model_stats[current_model]["input_tokens"] += input_tokens
                            model_stats[current_model]["output_tokens"] += output_tokens
                        except (ValueError, IndexError):
                            pass
                    elif current_model and line.startswith("Cost:"):
                        try:
                            cost_str = line.split(":")[1].strip().replace("$", "")
                            model_stats[current_model]["cost"] += float(cost_str)
                        except (ValueError, IndexError):
                            pass

    # Save session metadata
    with open(output_path / "session_meta.json", "w") as f:
        json.dump(session_meta, f, indent=2, ensure_ascii=False)

    # Save session timeline
    with open(output_path / "session_timeline.txt", "w") as f:
        f.write("\n".join(timeline_lines))

    # Build and save session cost summary
    cost_lines = ["SESSION COST SUMMARY", "=" * 80, ""]
    cost_lines.append(f"Session ID: {session_id}")
    cost_lines.append(f"Trace Count: {len(traces)}")
    cost_lines.append("")
    cost_lines.append("BY MODEL:")
    cost_lines.append("-" * 60)

    for model, stats in sorted(model_stats.items()):
        cost_lines.append(f"\n{model}:")
        cost_lines.append(f"  Calls: {stats['calls']}")
        cost_lines.append(f"  Tokens: {stats['input_tokens']:,} input / {stats['output_tokens']:,} output")
        cost_lines.append(f"  Cost: ${stats['cost']:.6f}")

    cost_lines.append("")
    cost_lines.append("=" * 60)
    cost_lines.append("GRAND TOTAL (all traces):")
    cost_lines.append(f"  Traces: {len(traces)}")
    cost_lines.append(f"  LLM Calls: {total_llm_calls}")
    cost_lines.append(f"  Input Tokens: {total_input_tokens:,}")
    cost_lines.append(f"  Output Tokens: {total_output_tokens:,}")
    cost_lines.append(f"  Total Cost: ${total_cost:.6f}")

    with open(output_path / "session_cost_summary.txt", "w") as f:
        f.write("\n".join(cost_lines))

    # Print results
    print(f"\nSession data saved to: {output_path}")
    print(f"\nFiles created:")
    print(f"  - session_meta.json          (session metadata)")
    print(f"  - session_timeline.txt       (chronological trace list)")
    print(f"  - session_cost_summary.txt   (aggregated costs)")
    print(f"  - traces/                    ({len(traces)} trace folders)")

    return str(output_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python fetch_trace.py <trace_id> [--force] [--fast]     # Fetch a single trace")
        print("  python fetch_trace.py --session <session_id> [--fast]   # Fetch all traces in a session")
        print("  python fetch_trace.py --list                            # List cached traces")
        print("  python fetch_trace.py --clean [days]                    # Delete traces older than N days (default: 7)")
        print("  python fetch_trace.py --clean-all                       # Delete all cached traces")
        print("")
        print("Options:")
        print("  --force    Re-fetch even if cached")
        print("  --fast     Skip individual observation files (faster, smaller)")
        print("  --session  Fetch all traces in a session (requires session ID)")
        print("")
        print("Examples:")
        print("  python fetch_trace.py abc123def456...              # Fetch single trace")
        print("  python fetch_trace.py --session sess_abc123...     # Fetch all traces in session")
        print("  python fetch_trace.py --session sess_abc123 --fast # Fast mode for session")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--list":
        list_cached_traces()
    elif arg == "--clean":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        clean_old_traces(days)
    elif arg == "--clean-all":
        clean_all_traces()
    elif arg == "--session":
        # Session mode: fetch all traces in a session
        if len(sys.argv) < 3:
            print("ERROR: --session requires a session ID")
            print("Usage: python fetch_trace.py --session <session_id> [--fast]")
            sys.exit(1)
        session_id = sys.argv[2]
        force = "--force" in sys.argv
        fast = "--fast" in sys.argv
        fetch_and_save_session(session_id, force=force, skip_obs_files=fast)
    else:
        # Assume it's a trace ID
        trace_id = arg
        force = "--force" in sys.argv
        fast = "--fast" in sys.argv
        fetch_and_save_trace(trace_id, force=force, skip_obs_files=fast)
