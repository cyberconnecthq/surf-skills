#!/usr/bin/env python3
"""Query engine for Hermod OpenAPI specs.

Fetches, caches, and queries the Hermod Swagger spec.
Primary source: live Hermod API at /v1/docs/swagger/doc.json
Fallback: monorepo file at hermod/docs/hermod/Hermod_swagger.json

Storage: ~/.surf-core/api-docs/
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

API_DOCS_DIR = Path.home() / ".surf-core" / "api-docs"
SEMANTIC_FILE = API_DOCS_DIR / "semantic-swagger.json"
REFERENCE_FILE = API_DOCS_DIR / "semantic-api-reference.md"
SYNC_META = API_DOCS_DIR / "sync_meta.json"


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


def sync(hermod_url, hermod_token, monorepo_root=None):
    """Fetch Swagger spec from live API or monorepo fallback."""
    API_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    results = {}

    # Clean up stale proxy file from old sync
    stale_proxy = API_DOCS_DIR / "proxy-openapi.json"
    if stale_proxy.exists():
        stale_proxy.unlink()

    swagger_synced = False

    # 1. Primary: fetch live Swagger from Hermod API (no auth needed)
    if hermod_url:
        try:
            r = subprocess.run(
                [
                    "curl", "-s", "--max-time", "30",
                    "-w", "\n%{http_code}",
                    f"{hermod_url}/v1/docs/swagger/doc.json",
                ],
                capture_output=True, text=True,
            )
            if r.returncode == 0 and r.stdout.strip():
                lines = r.stdout.rstrip().rsplit("\n", 1)
                body = lines[0] if len(lines) == 2 else r.stdout
                http_code = int(lines[1]) if len(lines) == 2 else 0

                if 200 <= http_code < 400:
                    data = json.loads(body)
                    if "paths" in data:
                        SEMANTIC_FILE.write_text(json.dumps(data, indent=2))
                        results["swagger"] = {
                            "status": "ok",
                            "endpoints": len(data["paths"]),
                            "source": "live_api",
                        }
                        swagger_synced = True
                else:
                    results["swagger_live"] = {
                        "status": "failed",
                        "error": f"HTTP {http_code}",
                    }
        except Exception as e:
            results["swagger_live"] = {"status": "failed", "error": str(e)}

    # 2. Fallback: copy Swagger from monorepo filesystem
    if not swagger_synced and monorepo_root:
        swagger_path = (
            Path(monorepo_root)
            / "hermod"
            / "docs"
            / "hermod"
            / "Hermod_swagger.json"
        )
        if swagger_path.exists():
            data = json.loads(swagger_path.read_text())
            SEMANTIC_FILE.write_text(json.dumps(data, indent=2))
            results["swagger"] = {
                "status": "ok",
                "endpoints": len(data.get("paths", {})),
                "source": "monorepo",
            }
            swagger_synced = True

    if not swagger_synced:
        results["swagger"] = {
            "status": "failed",
            "error": "Could not fetch from live API or monorepo",
        }

    # 3. Copy API reference markdown from monorepo (if available)
    if monorepo_root:
        ref_path = Path(monorepo_root) / "hermod" / "docs" / "semantic-api-reference.md"
        if ref_path.exists():
            REFERENCE_FILE.write_text(ref_path.read_text())
            results["reference_md"] = "ok"

    # Save sync metadata
    meta = {
        "synced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hermod_url": hermod_url,
        "api_docs_dir": str(API_DOCS_DIR),
        "files": {
            "swagger": str(SEMANTIC_FILE) if SEMANTIC_FILE.exists() else None,
            "reference_md": str(REFERENCE_FILE) if REFERENCE_FILE.exists() else None,
        },
        "results": results,
    }
    SYNC_META.write_text(json.dumps(meta, indent=2))
    return meta


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_specs():
    specs = {}
    if SEMANTIC_FILE.exists():
        specs["semantic"] = json.loads(SEMANTIC_FILE.read_text())
    return specs


def _ensure_specs():
    specs = _load_specs()
    if not specs:
        print(
            json.dumps({"error": "No API specs found. Run: surf-api sync"}),
            file=sys.stderr,
        )
        sys.exit(1)
    return specs


def _full_path(source_name, spec, path):
    if source_name == "semantic":
        base = spec.get("basePath", "")
        return base + path
    return path


def _extract_params(details):
    """Extract parameter list, marking required with *."""
    return [
        p["name"] + ("*" if p.get("required") else "")
        for p in details.get("parameters", [])
    ]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def endpoints(category=None, compact=False):
    """List all endpoints, optionally filtered by category."""
    specs = _ensure_specs()
    result = []

    for source_name, spec in specs.items():
        for path, methods in sorted(spec.get("paths", {}).items()):
            for method, details in methods.items():
                if method not in ("get", "post", "put", "delete", "patch"):
                    continue

                fp = _full_path(source_name, spec, path)
                entry = {
                    "method": method.upper(),
                    "path": fp,
                    "summary": details.get("summary", ""),
                    "source": source_name,
                }
                if not compact:
                    entry["tags"] = details.get("tags", [])
                    entry["params"] = _extract_params(details)

                result.append(entry)

    # Filter by category keyword
    if category:
        cl = category.lower()
        result = [
            e
            for e in result
            if cl in e["path"].lower()
            or cl in e.get("summary", "").lower()
            or any(cl in t.lower() for t in e.get("tags", []))
        ]

    return {"count": len(result), "endpoints": result}


# ---------------------------------------------------------------------------
# Show
# ---------------------------------------------------------------------------


def show(path_query):
    """Show full details for endpoints matching path_query."""
    specs = _ensure_specs()
    matches = []
    query = path_query.lower().strip("/")

    for source_name, spec in specs.items():
        host = spec.get("host", "")
        base = spec.get("basePath", "") if source_name == "semantic" else ""
        schemes = spec.get("schemes", ["https"])

        for path, methods in spec.get("paths", {}).items():
            fp = _full_path(source_name, spec, path)
            fp_normalized = fp.lower().strip("/")

            if query not in fp_normalized:
                continue

            for method, details in methods.items():
                if method not in ("get", "post", "put", "delete", "patch"):
                    continue

                params = details.get("parameters", [])

                # Build example curl
                curl_parts = ["curl -s"]
                curl_parts.append('-H "Authorization: Bearer $TOKEN"')

                if method != "get":
                    curl_parts.append(f"-X {method.upper()}")
                    curl_parts.append('-H "Content-Type: application/json"')

                # Build URL with query params
                url = f"$HERMOD_URL{fp}"
                query_params = [
                    p for p in params if p.get("in") == "query"
                ]
                if query_params:
                    qs = "&".join(
                        f"{p['name']}=<{p.get('type', 'value')}>"
                        for p in query_params
                        if p.get("required")
                    )
                    if qs:
                        url += f"?{qs}"
                curl_parts.append(f'"{url}"')

                endpoint = {
                    "method": method.upper(),
                    "path": fp,
                    "summary": details.get("summary", ""),
                    "description": details.get("description", ""),
                    "tags": details.get("tags", []),
                    "source": source_name,
                    "parameters": [
                        {
                            "name": p["name"],
                            "in": p.get("in", ""),
                            "required": p.get("required", False),
                            "type": p.get("type", p.get("schema", {}).get("type", "")),
                            "description": p.get("description", ""),
                        }
                        for p in params
                    ],
                    "curl_example": " \\\n  ".join(curl_parts),
                }
                matches.append(endpoint)

    if not matches:
        return {"error": f'No endpoint matching "{path_query}"', "hint": "Use: surf-api search <keyword>"}

    return {"count": len(matches), "endpoints": matches}


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def search(query):
    """Search endpoints by keyword across path, summary, description, params."""
    specs = _ensure_specs()
    query_lower = query.lower()
    matches = []

    for source_name, spec in specs.items():
        for path, methods in spec.get("paths", {}).items():
            fp = _full_path(source_name, spec, path)
            for method, details in methods.items():
                if method not in ("get", "post", "put", "delete", "patch"):
                    continue

                searchable = " ".join(
                    [
                        fp,
                        details.get("summary", ""),
                        details.get("description", ""),
                        " ".join(details.get("tags", [])),
                        " ".join(
                            p.get("name", "") + " " + p.get("description", "")
                            for p in details.get("parameters", [])
                        ),
                    ]
                ).lower()

                if query_lower in searchable:
                    matches.append(
                        {
                            "method": method.upper(),
                            "path": fp,
                            "summary": details.get("summary", ""),
                            "params": _extract_params(details),
                            "source": source_name,
                        }
                    )

    return {"count": len(matches), "endpoints": matches}


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


def status():
    """Show sync status and file info."""
    if not SYNC_META.exists():
        return {"error": "Never synced. Run: surf-api sync"}

    meta = json.loads(SYNC_META.read_text())

    # Add file sizes
    for key, path_str in meta.get("files", {}).items():
        if path_str and Path(path_str).exists():
            size = Path(path_str).stat().st_size
            meta["files"][key] = {
                "path": path_str,
                "size_kb": round(size / 1024, 1),
            }

    return meta


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: _api_query.py <command> [args]"}))
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "sync":
        hermod_url = sys.argv[2] if len(sys.argv) > 2 else ""
        hermod_token = sys.argv[3] if len(sys.argv) > 3 else ""
        monorepo = sys.argv[4] if len(sys.argv) > 4 else None
        result = sync(hermod_url, hermod_token, monorepo)
    elif cmd == "endpoints":
        cat = sys.argv[2] if len(sys.argv) > 2 else None
        compact = "--compact" in sys.argv
        result = endpoints(cat, compact)
    elif cmd == "show":
        if len(sys.argv) < 3:
            result = {"error": "Usage: surf-api show <path>"}
        else:
            result = show(sys.argv[2])
    elif cmd == "search":
        if len(sys.argv) < 3:
            result = {"error": "Usage: surf-api search <query>"}
        else:
            result = search(sys.argv[2])
    elif cmd == "status":
        result = status()
    else:
        result = {"error": f"Unknown command: {cmd}"}

    print(json.dumps(result, indent=2))
