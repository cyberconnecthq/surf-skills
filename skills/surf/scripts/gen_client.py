#!/usr/bin/env python3
"""
Generate typed API client code from surf CLI endpoint schemas.

Usage:
    python gen_client.py --ops market-price wallet-detail --lang typescript --out ./api/
    python gen_client.py --ops market-price --lang python --out ./api/
    python gen_client.py --ops market-price --lang typescript --hooks --out ./api/

Requires: surf CLI installed and authenticated (surf login).
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class SchemaField:
    name: str
    type_str: str  # 'string', 'integer', 'number', 'boolean', 'any', 'object'
    required: bool
    description: str
    format_str: Optional[str] = None
    default: Optional[str] = None
    enum_values: Optional[list[str]] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    children: list["SchemaField"] = dc_field(default_factory=list)
    is_array: bool = False


@dataclass
class Endpoint:
    name: str  # e.g. 'market-price'
    method: str  # 'GET' or 'POST'
    path: str  # e.g. '/market/price'
    description: str
    params: list[SchemaField]  # query params (GET)
    body_fields: list[SchemaField]  # body fields (POST)
    data_fields: list[SchemaField]  # fields inside response data
    data_is_array: bool  # True → data: [...], False → data: {...}
    pagination: str  # 'none', 'offset', 'cursor'


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://api.ask.surf/gateway/v1"

# Longest-first for greedy matching.
DOMAIN_PREFIXES = sorted(
    [
        "prediction-market", "polymarket", "kalshi",
        "market", "wallet", "social", "token", "project",
        "fund", "onchain", "news", "exchange", "search", "web",
    ],
    key=len,
    reverse=True,
)


# ---------------------------------------------------------------------------
# URL mapping
# ---------------------------------------------------------------------------

def op_to_path(op: str) -> str:
    """Convert operation name to API path: 'market-price' → '/market/price'."""
    for prefix in DOMAIN_PREFIXES:
        if op == prefix:
            return f"/{prefix}"
        if op.startswith(prefix + "-"):
            rest = op[len(prefix) + 1:]
            return f"/{prefix}/{rest}"
    # Fallback: split at first hyphen.
    parts = op.split("-", 1)
    return "/" + "/".join(parts)


# ---------------------------------------------------------------------------
# Help text parser
# ---------------------------------------------------------------------------

# Matches a field line: `  name[*]: (type attrs) description`
# Also matches `  --flag-name: ...` for option schemas.
_FIELD_RE = re.compile(
    r"^(\s*)"              # indentation
    r"(--)?(\$?\w[\w-]*)"  # optional --, then field name
    r"(\*)?"               # optional required marker
    r":\s+"                # colon + space
    r"(.*)"                # rest of line
)

# Type annotation: `(string default:"30d" enum:"a","b" min:1 max:100 format:int64)`
_TYPE_RE = re.compile(r"^\(([^)]+)\)\s*(.*)?$")

_ENUM_RE = re.compile(r'enum:"([^"]*(?:","[^"]*)*)"')
_DEFAULT_RE = re.compile(r'default:"?([^",\s)]+)"?')
_FORMAT_RE = re.compile(r"format:(\S+)")
_MIN_RE = re.compile(r"min:(\d+)")
_MAX_RE = re.compile(r"max:(\d+)")


def _parse_type_annotation(text: str) -> tuple[SchemaField, str]:
    """Parse '(type attrs) description' into partial SchemaField + description."""
    m = _TYPE_RE.match(text)
    if not m:
        return SchemaField(name="", type_str="any", required=False, description=text.strip()), ""
    inner, desc = m.group(1), (m.group(2) or "").strip()
    parts = inner.split(None, 1)
    type_str = parts[0]
    attrs = parts[1] if len(parts) > 1 else ""

    enum_m = _ENUM_RE.search(attrs)
    default_m = _DEFAULT_RE.search(attrs)
    format_m = _FORMAT_RE.search(attrs)
    min_m = _MIN_RE.search(attrs)
    max_m = _MAX_RE.search(attrs)

    return SchemaField(
        name="",
        type_str=type_str,
        required=False,
        description=desc,
        format_str=format_m.group(1) if format_m else None,
        default=default_m.group(1) if default_m else None,
        enum_values=enum_m.group(1).split('","') if enum_m else None,
        min_val=float(min_m.group(1)) if min_m else None,
        max_val=float(max_m.group(1)) if max_m else None,
    ), desc


def _parse_schema_lines(lines: list[str], start: int = 0) -> tuple[list[SchemaField], int]:
    """Recursively parse schema lines into a list of SchemaField objects.

    Returns (fields, next_line_index).
    """
    fields: list[SchemaField] = []
    i = start
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines and schema delimiters.
        if not stripped or stripped in ("```schema", "```"):
            i += 1
            continue

        # End of current nesting level.
        if stripped in ("}", "]", "},", "],"):
            return fields, i + 1

        # Anonymous object start (inside array): `{`
        if stripped == "{":
            children, i = _parse_schema_lines(lines, i + 1)
            if children:
                # Attach to parent's last array field or create anonymous.
                if fields and fields[-1].is_array and not fields[-1].children:
                    fields[-1].children = children
                else:
                    fields.extend(children)
            continue

        # Dynamic keys: `<any>: <any>`
        if stripped.startswith("<any>"):
            fields.append(SchemaField(
                name="*", type_str="any", required=False,
                description="Dynamic keys",
            ))
            i += 1
            continue

        # Field definition.
        m = _FIELD_RE.match(line)
        if not m:
            i += 1
            continue

        _prefix, _dash, name, req_mark, rest = m.groups()
        # Clean up CLI flag names: --time-range → time_range
        if _dash:
            name = name.lstrip("-")
        name = name.replace("-", "_")
        required = req_mark == "*"
        rest = rest.strip()

        # Skip $schema field.
        if name == "$schema":
            i += 1
            continue

        # Check if rest starts with `[` or `{` (nested structure).
        if rest == "[" or rest.startswith("["):
            field = SchemaField(
                name=name, type_str="array", required=required,
                description="", is_array=True,
            )
            # Parse children inside the array.
            field.children, i = _parse_schema_lines(lines, i + 1)
            fields.append(field)
            continue

        if rest == "{" or rest.startswith("{"):
            field = SchemaField(
                name=name, type_str="object", required=required,
                description="",
            )
            field.children, i = _parse_schema_lines(lines, i + 1)
            fields.append(field)
            continue

        # Regular field with type annotation.
        partial, desc = _parse_type_annotation(rest)
        partial.name = name
        partial.required = required
        if not partial.description:
            partial.description = desc
        fields.append(partial)
        i += 1

    return fields, i


def _extract_schema_block(text: str, header: str) -> list[str]:
    """Extract lines of a ```schema block following a header pattern."""
    lines = text.split("\n")
    in_block = False
    result = []
    found_header = False
    for line in lines:
        if header in line:
            found_header = True
            continue
        if found_header and "```schema" in line:
            in_block = True
            continue
        if in_block:
            if line.strip() == "```":
                break
            result.append(line)
    return result


def _detect_method(help_text: str) -> str:
    """Detect HTTP method from help text."""
    if "## Request Schema" in help_text or "## Input Example" in help_text:
        return "POST"
    return "GET"


def _detect_pagination(params: list[SchemaField], data_fields: list[SchemaField],
                        meta_text: str) -> str:
    """Detect pagination type from params and meta fields."""
    param_names = {p.name for p in params}
    if "cursor" in param_names and "next_cursor" in meta_text:
        return "cursor"
    if "offset" in param_names and "total" in meta_text:
        return "offset"
    return "none"


def parse_help(op: str, help_text: str) -> Endpoint:
    """Parse surf <op> --help output into an Endpoint."""
    # Description: first paragraph before ## headings.
    desc_lines = []
    for line in help_text.split("\n"):
        if line.startswith("##"):
            break
        if line.strip():
            desc_lines.append(line.strip())
    description = " ".join(desc_lines)

    method = _detect_method(help_text)

    # Parse option/request schema.
    params: list[SchemaField] = []
    body_fields: list[SchemaField] = []
    if method == "GET":
        option_lines = _extract_schema_block(help_text, "## Option Schema")
        if option_lines:
            params, _ = _parse_schema_lines(option_lines)
    else:
        request_lines = _extract_schema_block(help_text, "## Request Schema")
        if request_lines:
            body_fields, _ = _parse_schema_lines(request_lines)

    # Parse response schema.
    response_lines = _extract_schema_block(help_text, "## Response 200")
    resp_fields: list[SchemaField] = []
    if response_lines:
        resp_fields, _ = _parse_schema_lines(response_lines)

    # Find `data` field to determine shape.
    data_fields: list[SchemaField] = []
    data_is_array = True
    for f in resp_fields:
        if f.name == "data":
            data_is_array = f.is_array
            data_fields = f.children
            break

    # Get meta text for pagination detection.
    meta_text = ""
    for f in resp_fields:
        if f.name == "meta":
            meta_text = " ".join(c.name for c in f.children)
            break

    pagination = _detect_pagination(params, data_fields, meta_text)

    return Endpoint(
        name=op,
        method=method,
        path=op_to_path(op),
        description=description,
        params=params,
        body_fields=body_fields,
        data_fields=data_fields,
        data_is_array=data_is_array,
        pagination=pagination,
    )


# ---------------------------------------------------------------------------
# Name helpers
# ---------------------------------------------------------------------------

def _pascal(name: str) -> str:
    """'market-price' → 'MarketPrice'."""
    return "".join(w.capitalize() for w in re.split(r"[-_]", name))


def _snake(name: str) -> str:
    """'market-price' → 'market_price'."""
    return name.replace("-", "_")


def _ts_type(field: SchemaField) -> str:
    """Convert a SchemaField to a TypeScript type string."""
    if field.enum_values:
        return " | ".join(f"'{v}'" for v in field.enum_values)
    if field.is_array and field.children:
        # Array of objects — reference the parent interface.
        return f"{_pascal(field.name)}Item[]"
    if field.children:
        return _pascal(field.name)
    m = {"string": "string", "integer": "number", "number": "number",
         "boolean": "boolean", "any": "unknown"}
    return m.get(field.type_str, "unknown")


def _py_type(field: SchemaField) -> str:
    """Convert a SchemaField to a Python type string."""
    if field.enum_values:
        return "str"  # Use Literal in type annotation separately.
    if field.is_array and field.children:
        return f"list[{_pascal(field.name)}Item]"
    if field.children:
        return _pascal(field.name)
    m = {"string": "str", "integer": "int", "number": "float",
         "boolean": "bool", "any": "Any"}
    return m.get(field.type_str, "Any")


# ---------------------------------------------------------------------------
# TypeScript generator
# ---------------------------------------------------------------------------

def _gen_ts_interface(name: str, fields: list[SchemaField], lines: list[str],
                      nested_interfaces: list[tuple[str, list[SchemaField]]]):
    """Generate a TypeScript interface and collect nested interfaces."""
    lines.append(f"export interface {name} {{")
    for f in fields:
        if f.name == "*":  # dynamic keys
            lines.append("  [key: string]: unknown;")
            continue
        opt = "" if f.required else "?"
        if f.description:
            lines.append(f"  /** {f.description} */")
        if f.is_array and f.children:
            child_name = f"{name}{_pascal(f.name)}Item"
            lines.append(f"  {f.name}{opt}: {child_name}[];")
            nested_interfaces.append((child_name, f.children))
        elif f.children:
            child_name = f"{name}{_pascal(f.name)}"
            lines.append(f"  {f.name}{opt}: {child_name};")
            nested_interfaces.append((child_name, f.children))
        else:
            lines.append(f"  {f.name}{opt}: {_ts_type(f)};")
    lines.append("}")
    lines.append("")


def generate_typescript(endpoints: list[Endpoint], output_dir: Path, *,
                        hooks: bool = False):
    """Generate TypeScript client files."""
    type_lines: list[str] = []
    client_lines: list[str] = []
    hook_lines: list[str] = []

    # --- types.ts ---
    type_lines.append("// Auto-generated by gen_client.py — do not edit.")
    type_lines.append("")
    type_lines.append("export interface ResponseMeta {")
    type_lines.append("  cached?: boolean;")
    type_lines.append("  credits_used?: number;")
    type_lines.append("  total?: number;")
    type_lines.append("  limit?: number;")
    type_lines.append("  offset?: number;")
    type_lines.append("}")
    type_lines.append("")
    type_lines.append("export interface CursorMeta {")
    type_lines.append("  cached?: boolean;")
    type_lines.append("  credits_used?: number;")
    type_lines.append("  has_more?: boolean;")
    type_lines.append("  next_cursor?: string;")
    type_lines.append("  limit?: number;")
    type_lines.append("}")
    type_lines.append("")
    type_lines.append("export interface ApiResponse<T> { data: T[]; meta?: ResponseMeta; }")
    type_lines.append("export interface ApiObjectResponse<T> { data: T; meta?: ResponseMeta; }")
    type_lines.append("export interface ApiCursorResponse<T> { data: T[]; meta?: CursorMeta; }")
    type_lines.append("")

    for ep in endpoints:
        pascal = _pascal(ep.name)
        item_name = f"{pascal}Item" if ep.data_is_array else f"{pascal}Data"

        # Generate data interfaces.
        nested: list[tuple[str, list[SchemaField]]] = []
        _gen_ts_interface(item_name, ep.data_fields, type_lines, nested)
        while nested:
            n, f = nested.pop(0)
            _gen_ts_interface(n, f, type_lines, nested)

        # Generate params interface (GET) or body interface (POST).
        param_fields = ep.params if ep.method == "GET" else ep.body_fields
        if param_fields:
            type_lines.append(f"export interface {pascal}Params {{")
            for p in param_fields:
                opt = "" if p.required else "?"
                if p.description:
                    doc_parts = [p.description]
                    if p.default:
                        doc_parts.append(f"@default '{p.default}'")
                    if p.min_val is not None:
                        doc_parts.append(f"@min {int(p.min_val)}")
                    if p.max_val is not None:
                        doc_parts.append(f"@max {int(p.max_val)}")
                    type_lines.append(f"  /** {' — '.join(doc_parts)} */")
                type_lines.append(f"  {p.name}{opt}: {_ts_type(p)};")
            type_lines.append("}")
            type_lines.append("")

    # --- client.ts ---
    client_lines.append("// Auto-generated by gen_client.py — do not edit.")
    client_lines.append("")

    # Collect imports.
    type_imports: list[str] = []
    for ep in endpoints:
        pascal = _pascal(ep.name)
        item_name = f"{pascal}Item" if ep.data_is_array else f"{pascal}Data"
        param_fields = ep.params if ep.method == "GET" else ep.body_fields
        if ep.data_is_array:
            if ep.pagination == "cursor":
                type_imports.append("ApiCursorResponse")
            else:
                type_imports.append("ApiResponse")
        else:
            type_imports.append("ApiObjectResponse")
        type_imports.append(item_name)
        if param_fields:
            type_imports.append(f"{pascal}Params")
    type_imports = sorted(set(type_imports))
    client_lines.append(f"import type {{ {', '.join(type_imports)} }} from './types';")
    client_lines.append("")
    client_lines.append(f"const BASE_URL = '{BASE_URL}';")
    client_lines.append("")

    for ep in endpoints:
        pascal = _pascal(ep.name)
        func = f"fetch{pascal}"
        item_name = f"{pascal}Item" if ep.data_is_array else f"{pascal}Data"
        param_fields = ep.params if ep.method == "GET" else ep.body_fields
        has_params = bool(param_fields)
        params_optional = has_params and not any(p.required for p in param_fields)

        # Return type.
        if ep.data_is_array:
            ret = f"ApiCursorResponse<{item_name}>" if ep.pagination == "cursor" else f"ApiResponse<{item_name}>"
        else:
            ret = f"ApiObjectResponse<{item_name}>"

        # JSDoc.
        if ep.description:
            client_lines.append(f"/** {ep.description} */")

        # Function signature.
        opt = "?" if params_optional else ""
        if ep.method == "GET":
            if has_params:
                client_lines.append(f"export async function {func}(params{opt}: {pascal}Params, token?: string): Promise<{ret}> {{")
            else:
                client_lines.append(f"export async function {func}(token?: string): Promise<{ret}> {{")

            # Build query string.
            if has_params:
                client_lines.append("  const qs = new URLSearchParams();")
                for p in param_fields:
                    accessor = f"params{'?' if params_optional else ''}.{p.name}"
                    if p.type_str == "integer" or p.type_str == "number":
                        client_lines.append(f"  if ({accessor} != null) qs.set('{p.name}', String({accessor}));")
                    else:
                        client_lines.append(f"  if ({accessor} != null) qs.set('{p.name}', {accessor});")
                client_lines.append(f"  const url = `${{BASE_URL}}{ep.path}${{qs.size ? '?' + qs : ''}}`;")
            else:
                client_lines.append(f"  const url = `${{BASE_URL}}{ep.path}`;")

            client_lines.append("  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });")
        else:
            # POST
            if has_params:
                client_lines.append(f"export async function {func}(body{opt}: {pascal}Params, token?: string): Promise<{ret}> {{")
            else:
                client_lines.append(f"export async function {func}(token?: string): Promise<{ret}> {{")
            client_lines.append(f"  const res = await fetch(`${{BASE_URL}}{ep.path}`, {{")
            client_lines.append("    method: 'POST',")
            client_lines.append("    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },")
            if has_params:
                client_lines.append("    body: JSON.stringify(body),")
            client_lines.append("  });")

        client_lines.append("  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);")
        client_lines.append("  return res.json();")
        client_lines.append("}")
        client_lines.append("")

    # --- hooks.ts (optional) ---
    if hooks:
        hook_lines.append("// Auto-generated by gen_client.py — do not edit.")
        hook_lines.append("")
        hook_lines.append("import { useQuery, useInfiniteQuery } from '@tanstack/react-query';")

        func_imports = []
        hook_type_imports = []
        for ep in endpoints:
            pascal = _pascal(ep.name)
            func_imports.append(f"fetch{pascal}")
            param_fields = ep.params if ep.method == "GET" else ep.body_fields
            if param_fields:
                hook_type_imports.append(f"{pascal}Params")
        hook_lines.append(f"import {{ {', '.join(func_imports)} }} from './client';")
        if hook_type_imports:
            hook_lines.append(f"import type {{ {', '.join(sorted(set(hook_type_imports)))} }} from './types';")
        hook_lines.append("")

        for ep in endpoints:
            pascal = _pascal(ep.name)
            func = f"fetch{pascal}"
            param_fields = ep.params if ep.method == "GET" else ep.body_fields
            has_params = bool(param_fields)
            params_type = f"{pascal}Params" if has_params else None

            if ep.pagination == "offset":
                # Infinite query with offset.
                if has_params:
                    hook_lines.append(f"export function useInfinite{pascal}(params?: Omit<{params_type}, 'offset'>, token?: string) {{")
                else:
                    hook_lines.append(f"export function useInfinite{pascal}(token?: string) {{")
                hook_lines.append("  return useInfiniteQuery({")
                hook_lines.append(f"    queryKey: ['{ep.name}', params],")
                if has_params:
                    hook_lines.append(f"    queryFn: ({{ pageParam = 0 }}) => {func}({{ ...params!, offset: pageParam }}, token),")
                else:
                    hook_lines.append(f"    queryFn: () => {func}(token),")
                hook_lines.append("    initialPageParam: 0,")
                hook_lines.append("    getNextPageParam: (last) => {")
                hook_lines.append("      const m = last?.meta;")
                hook_lines.append("      if (!m?.total || !m?.limit) return undefined;")
                hook_lines.append("      const next = (m.offset ?? 0) + m.limit;")
                hook_lines.append("      return next < m.total ? next : undefined;")
                hook_lines.append("    },")
                hook_lines.append("    enabled: !!token,")
                hook_lines.append("  });")
                hook_lines.append("}")
            elif ep.pagination == "cursor":
                # Infinite query with cursor.
                if has_params:
                    hook_lines.append(f"export function useInfinite{pascal}(params?: Omit<{params_type}, 'cursor'>, token?: string) {{")
                else:
                    hook_lines.append(f"export function useInfinite{pascal}(token?: string) {{")
                hook_lines.append("  return useInfiniteQuery({")
                hook_lines.append(f"    queryKey: ['{ep.name}', params],")
                if has_params:
                    hook_lines.append(f"    queryFn: ({{ pageParam }}) => {func}({{ ...params!, cursor: pageParam || undefined }}, token),")
                else:
                    hook_lines.append(f"    queryFn: () => {func}(token),")
                hook_lines.append("    initialPageParam: '',")
                hook_lines.append(f"    getNextPageParam: (last) => last?.meta?.has_more ? last.meta.next_cursor : undefined,")
                hook_lines.append("    enabled: !!token,")
                hook_lines.append("  });")
                hook_lines.append("}")
            else:
                # Standard query.
                if has_params:
                    hook_lines.append(f"export function use{pascal}(params?: {params_type}, token?: string) {{")
                else:
                    hook_lines.append(f"export function use{pascal}(token?: string) {{")
                hook_lines.append("  return useQuery({")
                hook_lines.append(f"    queryKey: ['{ep.name}', params],")
                if has_params:
                    hook_lines.append(f"    queryFn: () => {func}(params, token),")
                else:
                    hook_lines.append(f"    queryFn: () => {func}(token),")
                hook_lines.append("    enabled: !!token,")
                hook_lines.append("  });")
                hook_lines.append("}")
            hook_lines.append("")

    # --- Write files ---
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "types.ts").write_text("\n".join(type_lines) + "\n")
    (output_dir / "client.ts").write_text("\n".join(client_lines) + "\n")
    written = ["types.ts", "client.ts"]
    if hooks and hook_lines:
        (output_dir / "hooks.ts").write_text("\n".join(hook_lines) + "\n")
        written.append("hooks.ts")
    return written


# ---------------------------------------------------------------------------
# Python generator
# ---------------------------------------------------------------------------

def generate_python(endpoints: list[Endpoint], output_dir: Path):
    """Generate Python client files."""
    type_lines: list[str] = []
    client_lines: list[str] = []

    # --- types.py ---
    type_lines.append('"""Auto-generated by gen_client.py — do not edit."""')
    type_lines.append("")
    type_lines.append("from __future__ import annotations")
    type_lines.append("")
    type_lines.append("from dataclasses import dataclass, field")
    type_lines.append("from typing import Any, Generic, TypeVar")
    type_lines.append("")
    type_lines.append("T = TypeVar('T')")
    type_lines.append("")
    type_lines.append("")
    type_lines.append("@dataclass")
    type_lines.append("class ResponseMeta:")
    type_lines.append("    cached: bool | None = None")
    type_lines.append("    credits_used: int | None = None")
    type_lines.append("    total: int | None = None")
    type_lines.append("    limit: int | None = None")
    type_lines.append("    offset: int | None = None")
    type_lines.append("")
    type_lines.append("")
    type_lines.append("@dataclass")
    type_lines.append("class CursorMeta:")
    type_lines.append("    cached: bool | None = None")
    type_lines.append("    credits_used: int | None = None")
    type_lines.append("    has_more: bool | None = None")
    type_lines.append("    next_cursor: str | None = None")
    type_lines.append("    limit: int | None = None")
    type_lines.append("")
    type_lines.append("")
    type_lines.append("@dataclass")
    type_lines.append("class ApiResponse(Generic[T]):")
    type_lines.append("    data: list[T]")
    type_lines.append("    meta: ResponseMeta | None = None")
    type_lines.append("")
    type_lines.append("")
    type_lines.append("@dataclass")
    type_lines.append("class ApiObjectResponse(Generic[T]):")
    type_lines.append("    data: T")
    type_lines.append("    meta: ResponseMeta | None = None")
    type_lines.append("")
    type_lines.append("")
    type_lines.append("@dataclass")
    type_lines.append("class ApiCursorResponse(Generic[T]):")
    type_lines.append("    data: list[T]")
    type_lines.append("    meta: CursorMeta | None = None")
    type_lines.append("")

    def _gen_py_dataclass(name: str, fields: list[SchemaField],
                          nested: list[tuple[str, list[SchemaField]]]):
        type_lines.append("")
        type_lines.append("@dataclass")
        type_lines.append(f"class {name}:")
        # Filter out dynamic-key markers.
        real_fields = [f for f in fields if f.name != "*"]
        if not real_fields:
            type_lines.append("    pass")
            return
        # Required fields first, then optional.
        required = [f for f in real_fields if f.required]
        optional = [f for f in real_fields if not f.required]
        for f in required + optional:
            py_t = _py_type(f)
            if f.is_array and f.children:
                child_name = f"{name}{_pascal(f.name)}Item"
                py_t = f"list[{child_name}]"
                nested.append((child_name, f.children))
            elif f.children:
                child_name = f"{name}{_pascal(f.name)}"
                py_t = child_name
                nested.append((child_name, f.children))
            if f.description:
                type_lines.append(f"    # {f.description}")
            if f.required:
                type_lines.append(f"    {f.name}: {py_t}")
            else:
                type_lines.append(f"    {f.name}: {py_t} | None = None")
        type_lines.append("")

    for ep in endpoints:
        pascal = _pascal(ep.name)
        item_name = f"{pascal}Item" if ep.data_is_array else f"{pascal}Data"
        nested: list[tuple[str, list[SchemaField]]] = []
        # Generate nested types first (forward declarations via __future__).
        _gen_py_dataclass(item_name, ep.data_fields, nested)
        while nested:
            n, f = nested.pop(0)
            _gen_py_dataclass(n, f, nested)

    # --- client.py ---
    client_lines.append('"""Auto-generated by gen_client.py — do not edit."""')
    client_lines.append("")
    client_lines.append("from __future__ import annotations")
    client_lines.append("")
    client_lines.append("import httpx")
    client_lines.append("")
    client_lines.append(f"BASE_URL = '{BASE_URL}'")
    client_lines.append("")
    client_lines.append("")
    client_lines.append("class SurfClient:")
    client_lines.append('    """Typed client for the Surf crypto data API."""')
    client_lines.append("")
    client_lines.append("    def __init__(self, token: str, base_url: str = BASE_URL) -> None:")
    client_lines.append("        self.base_url = base_url")
    client_lines.append("        self._client = httpx.Client(")
    client_lines.append("            base_url=base_url,")
    client_lines.append("            headers={'Authorization': f'Bearer {token}'},")
    client_lines.append("            timeout=30.0,")
    client_lines.append("        )")
    client_lines.append("")

    for ep in endpoints:
        snake = _snake(ep.name).replace("-", "_")
        func = f"fetch_{snake}"
        param_fields = ep.params if ep.method == "GET" else ep.body_fields

        # Build function signature.
        # Python reserved words that need renaming.
        _PY_RESERVED = {"from", "to", "in", "is", "as", "or", "and", "not", "class", "type"}

        sig_parts = ["self"]
        # Required params first, then optional — Python requires this ordering.
        sorted_params = sorted(param_fields, key=lambda p: (not p.required,))
        for p in sorted_params:
            py_t = _py_type(p)
            if p.enum_values:
                py_t = "str"
            pname = f"{p.name}_" if p.name in _PY_RESERVED else p.name
            if p.required:
                sig_parts.append(f"{pname}: {py_t}")
            else:
                default = f"'{p.default}'" if p.default else "None"
                sig_parts.append(f"{pname}: {py_t} | None = {default}")

        client_lines.append(f"    def {func}({', '.join(sig_parts)}) -> dict:")
        if ep.description:
            client_lines.append(f'        """{ep.description}"""')

        if ep.method == "GET":
            # Build params dict.
            client_lines.append("        params = {}")
            for p in param_fields:
                pname = f"{p.name}_" if p.name in _PY_RESERVED else p.name
                client_lines.append(f"        if {pname} is not None:")
                client_lines.append(f"            params['{p.name}'] = {pname}")
            client_lines.append(f"        resp = self._client.get('{ep.path}', params=params)")
        else:
            client_lines.append("        body = {}")
            for p in param_fields:
                pname = f"{p.name}_" if p.name in _PY_RESERVED else p.name
                if p.required:
                    client_lines.append(f"        body['{p.name}'] = {pname}")
                else:
                    client_lines.append(f"        if {pname} is not None:")
                    client_lines.append(f"            body['{p.name}'] = {pname}")
            client_lines.append(f"        resp = self._client.post('{ep.path}', json=body)")

        client_lines.append("        resp.raise_for_status()")
        client_lines.append("        return resp.json()")
        client_lines.append("")

    # Pagination helpers.
    client_lines.append("    def fetch_all_pages(self, method, **kwargs) -> list:")
    client_lines.append('        """Fetch all pages for an offset-paginated endpoint."""')
    client_lines.append("        items, offset = [], 0")
    client_lines.append("        while True:")
    client_lines.append("            data = method(**kwargs, offset=offset, limit=100)")
    client_lines.append("            items.extend(data.get('data', []))")
    client_lines.append("            meta = data.get('meta', {})")
    client_lines.append("            total = meta.get('total')")
    client_lines.append("            if not total or offset + meta.get('limit', 100) >= total:")
    client_lines.append("                break")
    client_lines.append("            offset += meta['limit']")
    client_lines.append("        return items")
    client_lines.append("")
    client_lines.append("    def fetch_all_cursor(self, method, **kwargs) -> list:")
    client_lines.append('        """Fetch all pages for a cursor-paginated endpoint."""')
    client_lines.append("        items, cursor = [], None")
    client_lines.append("        while True:")
    client_lines.append("            if cursor:")
    client_lines.append("                kwargs['cursor'] = cursor")
    client_lines.append("            data = method(**kwargs)")
    client_lines.append("            items.extend(data.get('data', []))")
    client_lines.append("            meta = data.get('meta', {})")
    client_lines.append("            if not meta.get('has_more'):")
    client_lines.append("                break")
    client_lines.append("            cursor = meta.get('next_cursor')")
    client_lines.append("        return items")
    client_lines.append("")

    # --- Write files ---
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "types.py").write_text("\n".join(type_lines) + "\n")
    (output_dir / "client.py").write_text("\n".join(client_lines) + "\n")
    (output_dir / "__init__.py").write_text(
        "from .types import *  # noqa: F401,F403\n"
        "from .client import SurfClient  # noqa: F401\n"
    )
    return ["types.py", "client.py", "__init__.py"]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate typed API client code from surf CLI endpoint schemas.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --ops market-price wallet-detail --lang typescript --out ./api/
  %(prog)s --ops market-price --lang python --out ./api/
  %(prog)s --ops market-price --lang typescript --hooks --out ./api/
        """,
    )
    parser.add_argument("--ops", nargs="+", required=True,
                        help="Operation names (e.g. market-price wallet-detail)")
    parser.add_argument("--lang", choices=["typescript", "python"], default="typescript",
                        help="Target language (default: typescript)")
    parser.add_argument("--out", default="./api",
                        help="Output directory (default: ./api)")
    parser.add_argument("--hooks", action="store_true",
                        help="Generate React Query hooks (TypeScript only)")
    args = parser.parse_args()

    # 1. Sync.
    print("Syncing surf CLI cache...")
    result = subprocess.run(["surf", "sync"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Warning: surf sync failed: {result.stderr.strip()}", file=sys.stderr)

    # 2. Discover and parse.
    endpoints: list[Endpoint] = []
    for op in args.ops:
        print(f"Reading schema: surf {op} --help")
        result = subprocess.run(["surf", op, "--help"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: surf {op} --help failed: {result.stderr.strip()}", file=sys.stderr)
            sys.exit(1)
        help_text = result.stdout or result.stderr
        ep = parse_help(op, help_text)
        endpoints.append(ep)
        print(f"  → {ep.method} {ep.path} ({len(ep.data_fields)} fields, pagination={ep.pagination})")

    # 3. Generate.
    output_dir = Path(args.out)
    if args.lang == "typescript":
        written = generate_typescript(endpoints, output_dir, hooks=args.hooks)
    else:
        written = generate_python(endpoints, output_dir)

    print(f"\nGenerated {len(written)} files in {output_dir}/:")
    for f in written:
        print(f"  {f}")


if __name__ == "__main__":
    main()
