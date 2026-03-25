"""Tests for gen_client.py — parser, URL mapping, and code generation."""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Add scripts dir to path so we can import gen_client
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "surf" / "scripts"))

from gen_client import (
    Endpoint,
    SchemaField,
    _detect_method,
    _detect_pagination,
    _extract_schema_block,
    _parse_schema_lines,
    _pascal,
    _snake,
    _ts_type,
    generate_python,
    generate_typescript,
    op_to_path,
    parse_help,
)


# ---------------------------------------------------------------------------
# URL mapping
# ---------------------------------------------------------------------------


class TestOpToPath:
    def test_simple(self):
        assert op_to_path("market-price") == "/market/price"

    def test_multi_segment(self):
        assert op_to_path("social-user-posts") == "/social/user-posts"

    def test_compound_domain(self):
        assert op_to_path("prediction-market-category-metrics") == "/prediction-market/category-metrics"

    def test_single_word_domain(self):
        assert op_to_path("news-feed") == "/news/feed"

    def test_kalshi(self):
        assert op_to_path("kalshi-events") == "/kalshi/events"

    def test_polymarket(self):
        assert op_to_path("polymarket-ranking") == "/polymarket/ranking"

    def test_domain_only(self):
        """Edge case: operation name matches domain exactly."""
        assert op_to_path("web") == "/web"


# ---------------------------------------------------------------------------
# Name helpers
# ---------------------------------------------------------------------------


class TestNameHelpers:
    def test_pascal_simple(self):
        assert _pascal("market-price") == "MarketPrice"

    def test_pascal_multi(self):
        assert _pascal("social-user-posts") == "SocialUserPosts"

    def test_snake(self):
        assert _snake("market-price") == "market_price"


# ---------------------------------------------------------------------------
# Schema parsing
# ---------------------------------------------------------------------------

MARKET_PRICE_HELP = """Get historical price data points for a token. Use `time_range` for predefined windows.
## Option Schema:
```schema
{
  --symbol: (string) Single token ticker symbol like `BTC`, `ETH`, or `SOL`
  --time-range: (string default:"30d" enum:"1d","7d","14d","30d","90d","180d","365d","max") Predefined time range
  --from: (string) Start of custom date range
  --to: (string) End of custom date range
  --currency: (string default:"usd") Quote currency
}
```

## Response 200 (application/json)

OK

```schema
{
  $schema: (string format:uri) A URL to the JSON Schema for this object.
  data*: [
    {
      metric: (string) Metric name like `nupl`, `sopr`, or `price`
      symbol: (string) Token symbol this data point belongs to
      timestamp*: (integer format:int64) Unix timestamp in seconds
      value*: (number format:double) Metric value at this timestamp
    }
  ]
  meta*: {
    cached*: (boolean) Whether this response was served from cache
    credits_used*: (integer format:int64) Credits deducted for this request
  }
}
```

## Response default (application/json)

Error

Usage:
  surf surf market-price [flags]
"""

ONCHAIN_SQL_HELP = """Execute a raw SQL SELECT query against blockchain data.
## Input Example

```json
{
  "max_rows": 1000,
  "sql": "SELECT transaction_hash FROM agent.ethereum_transactions LIMIT 5"
}
```

## Request Schema (application/json)

```schema
{
  max_rows: (integer min:1 max:10000 default:1000 format:int64) Maximum number of rows
  sql*: (string) SQL query to execute
}
```

## Response 200 (application/json)

OK

```schema
{
  $schema: (string format:uri) A URL to the JSON Schema for this object.
  data*: [
    {
      <any>: <any>
    }
  ]
  meta*: {
    cached*: (boolean) Whether cached
    credits_used*: (integer format:int64) Credits deducted
    limit*: (integer format:int64) Max items
    offset*: (integer format:int64) Pagination offset
    total: (integer format:int64) Total matching items
  }
}
```

Usage:
  surf surf onchain-sql [flags]
"""

SOCIAL_USER_POSTS_HELP = """Get recent X (Twitter) posts by a specific user.
## Option Schema:
```schema
{
  --handle: (string) X (Twitter) username without @
  --limit: (integer min:1 max:100 default:20 format:int64) Results per page
  --cursor: (string) Opaque cursor token from previous response
  --filter: (string default:"all" enum:"all","original") Filter tweets
}
```

## Response 200 (application/json)

OK

```schema
{
  $schema: (string format:uri) URL.
  data*: [
    {
      author*: {
        avatar: (string) Profile picture URL
        handle*: (string) X handle without @
        name*: (string) Display name
        user_id*: (string) Numeric user ID
      }
      created_at*: (integer format:int64) Unix timestamp
      text*: (string) Full text content
      tweet_id*: (string) Numeric tweet ID
      url*: (string) Permanent link
    }
  ]
  meta*: {
    cached*: (boolean) Cached
    credits_used*: (integer format:int64) Credits
    has_more*: (boolean) Whether more items exist
    limit*: (integer format:int64) Max items
    next_cursor: (string) Opaque cursor for next page
  }
}
```

Usage:
  surf surf social-user-posts [flags]
"""


class TestDetectMethod:
    def test_get(self):
        assert _detect_method(MARKET_PRICE_HELP) == "GET"

    def test_post(self):
        assert _detect_method(ONCHAIN_SQL_HELP) == "POST"


class TestExtractSchemaBlock:
    def test_option_schema(self):
        lines = _extract_schema_block(MARKET_PRICE_HELP, "## Option Schema")
        assert len(lines) > 0
        joined = "\n".join(lines)
        assert "--symbol" in joined

    def test_response_schema(self):
        lines = _extract_schema_block(MARKET_PRICE_HELP, "## Response 200")
        assert len(lines) > 0
        joined = "\n".join(lines)
        assert "timestamp" in joined

    def test_request_schema(self):
        lines = _extract_schema_block(ONCHAIN_SQL_HELP, "## Request Schema")
        assert len(lines) > 0
        joined = "\n".join(lines)
        assert "sql" in joined


class TestParseSchemaLines:
    def test_simple_fields(self):
        lines = _extract_schema_block(MARKET_PRICE_HELP, "## Option Schema")
        fields, _ = _parse_schema_lines(lines)
        names = [f.name for f in fields]
        assert "symbol" in names
        assert "time_range" in names
        assert "currency" in names

    def test_required_fields(self):
        lines = _extract_schema_block(MARKET_PRICE_HELP, "## Response 200")
        fields, _ = _parse_schema_lines(lines)
        data_field = next(f for f in fields if f.name == "data")
        assert data_field.is_array
        assert data_field.required
        # Check children.
        child_names = {c.name for c in data_field.children}
        assert "timestamp" in child_names
        assert "value" in child_names
        ts = next(c for c in data_field.children if c.name == "timestamp")
        assert ts.required
        val = next(c for c in data_field.children if c.name == "value")
        assert val.required
        metric = next(c for c in data_field.children if c.name == "metric")
        assert not metric.required

    def test_enum_values(self):
        lines = _extract_schema_block(MARKET_PRICE_HELP, "## Option Schema")
        fields, _ = _parse_schema_lines(lines)
        tr = next(f for f in fields if f.name == "time_range")
        assert tr.enum_values == ["1d", "7d", "14d", "30d", "90d", "180d", "365d", "max"]
        assert tr.default == "30d"

    def test_nested_object(self):
        lines = _extract_schema_block(SOCIAL_USER_POSTS_HELP, "## Response 200")
        fields, _ = _parse_schema_lines(lines)
        data_field = next(f for f in fields if f.name == "data")
        author = next(c for c in data_field.children if c.name == "author")
        assert author.required
        assert len(author.children) > 0
        handle = next(c for c in author.children if c.name == "handle")
        assert handle.required

    def test_dynamic_keys(self):
        lines = _extract_schema_block(ONCHAIN_SQL_HELP, "## Response 200")
        fields, _ = _parse_schema_lines(lines)
        data_field = next(f for f in fields if f.name == "data")
        assert data_field.is_array
        assert any(c.name == "*" for c in data_field.children)

    def test_min_max(self):
        lines = _extract_schema_block(ONCHAIN_SQL_HELP, "## Request Schema")
        fields, _ = _parse_schema_lines(lines)
        max_rows = next(f for f in fields if f.name == "max_rows")
        assert max_rows.min_val == 1
        assert max_rows.max_val == 10000
        assert max_rows.default == "1000"


class TestDetectPagination:
    def test_no_pagination(self):
        ep = parse_help("market-price", MARKET_PRICE_HELP)
        assert ep.pagination == "none"

    def test_cursor_pagination(self):
        ep = parse_help("social-user-posts", SOCIAL_USER_POSTS_HELP)
        assert ep.pagination == "cursor"

    def test_offset_pagination_from_params(self):
        """Endpoint with offset/limit params and meta.total → offset pagination."""
        help_text = """Get token rankings.
## Option Schema:
```schema
{
  --sort-by: (string default:"market_cap") Sort field
  --limit: (integer min:1 max:100 default:20 format:int64) Results per page
  --offset: (integer min:0 default:0 format:int64) Pagination offset
}
```

## Response 200 (application/json)

OK

```schema
{
  data*: [
    {
      symbol*: (string) Token symbol
      price*: (number format:double) Price USD
    }
  ]
  meta*: {
    total*: (integer format:int64) Total items
    limit*: (integer format:int64) Limit
    offset*: (integer format:int64) Offset
    cached*: (boolean) Cached
    credits_used*: (integer format:int64) Credits
  }
}
```

Usage:
  surf surf market-ranking [flags]
"""
        ep = parse_help("market-ranking", help_text)
        assert ep.pagination == "offset"


# ---------------------------------------------------------------------------
# Full parse_help
# ---------------------------------------------------------------------------


class TestParseHelp:
    def test_get_endpoint(self):
        ep = parse_help("market-price", MARKET_PRICE_HELP)
        assert ep.method == "GET"
        assert ep.path == "/market/price"
        assert ep.data_is_array
        assert len(ep.params) == 5
        assert len(ep.data_fields) == 4

    def test_post_endpoint(self):
        ep = parse_help("onchain-sql", ONCHAIN_SQL_HELP)
        assert ep.method == "POST"
        assert ep.path == "/onchain/sql"
        assert len(ep.body_fields) == 2
        sql_field = next(f for f in ep.body_fields if f.name == "sql")
        assert sql_field.required

    def test_cursor_endpoint(self):
        ep = parse_help("social-user-posts", SOCIAL_USER_POSTS_HELP)
        assert ep.pagination == "cursor"
        assert ep.data_is_array
        # Check nested author object.
        author = next((f for f in ep.data_fields if f.name == "author"), None)
        assert author is not None
        assert len(author.children) >= 3

    def test_object_response(self):
        """wallet-detail returns data as object, not array."""
        help_text = """Get wallet detail.
## Option Schema:
```schema
{
  --address: (string) Wallet address
}
```

## Response 200 (application/json)

OK

```schema
{
  data*: {
    evm_balance: {
      address*: (string) Wallet address
      total_usd*: (number format:double) Total USD
    }
    labels: {
      address*: (string) Address
      entity_name: (string) Entity name
    }
  }
  meta*: {
    cached*: (boolean) Cached
    credits_used*: (integer format:int64) Credits
  }
}
```

Usage:
  surf surf wallet-detail [flags]
"""
        ep = parse_help("wallet-detail", help_text)
        assert not ep.data_is_array
        assert ep.path == "/wallet/detail"


# ---------------------------------------------------------------------------
# TypeScript generation
# ---------------------------------------------------------------------------


class TestGenerateTypescript:
    def test_generates_files(self, tmp_path):
        ep = parse_help("market-price", MARKET_PRICE_HELP)
        files = generate_typescript([ep], tmp_path)
        assert "types.ts" in files
        assert "client.ts" in files

    def test_types_content(self, tmp_path):
        ep = parse_help("market-price", MARKET_PRICE_HELP)
        generate_typescript([ep], tmp_path)
        content = (tmp_path / "types.ts").read_text()
        assert "MarketPriceItem" in content
        assert "timestamp: number;" in content
        assert "value: number;" in content
        assert "metric?: string;" in content
        assert "MarketPriceParams" in content
        assert "'1d' | '7d'" in content

    def test_client_content(self, tmp_path):
        ep = parse_help("market-price", MARKET_PRICE_HELP)
        generate_typescript([ep], tmp_path)
        content = (tmp_path / "client.ts").read_text()
        assert "fetchMarketPrice" in content
        assert "/market/price" in content
        assert "Bearer ${token}" in content
        assert "ApiResponse<MarketPriceItem>" in content

    def test_gateway_url_env_var(self, tmp_path):
        ep = parse_help("market-price", MARKET_PRICE_HELP)
        generate_typescript([ep], tmp_path)
        content = (tmp_path / "client.ts").read_text()
        assert "process.env.SURF_BASE_URL" in content
        assert "api.ask.surf/gateway/v1" in content

    def test_hooks_generated(self, tmp_path):
        ep = parse_help("market-price", MARKET_PRICE_HELP)
        files = generate_typescript([ep], tmp_path, hooks=True)
        assert "hooks.ts" in files
        content = (tmp_path / "hooks.ts").read_text()
        assert "useMarketPrice" in content
        assert "useQuery" in content

    def test_cursor_hook(self, tmp_path):
        ep = parse_help("social-user-posts", SOCIAL_USER_POSTS_HELP)
        generate_typescript([ep], tmp_path, hooks=True)
        content = (tmp_path / "hooks.ts").read_text()
        assert "useInfiniteSocialUserPosts" in content
        assert "useInfiniteQuery" in content
        assert "initialPageParam: ''" in content
        assert "has_more" in content

    def test_post_endpoint(self, tmp_path):
        ep = parse_help("onchain-sql", ONCHAIN_SQL_HELP)
        generate_typescript([ep], tmp_path)
        content = (tmp_path / "client.ts").read_text()
        assert "fetchOnchainSql" in content
        assert "method: 'POST'" in content
        assert "JSON.stringify(body)" in content

    def test_object_response_type(self, tmp_path):
        help_text = """Get wallet detail.
## Option Schema:
```schema
{
  --address: (string) Wallet address
}
```

## Response 200 (application/json)

OK

```schema
{
  data*: {
    total_usd*: (number format:double) Total
  }
  meta*: {
    cached*: (boolean) Cached
    credits_used*: (integer format:int64) Credits
  }
}
```

Usage:
  surf surf wallet-detail [flags]
"""
        ep = parse_help("wallet-detail", help_text)
        generate_typescript([ep], tmp_path)
        content = (tmp_path / "client.ts").read_text()
        assert "ApiObjectResponse<WalletDetailData>" in content

    def test_multiple_endpoints(self, tmp_path):
        ep1 = parse_help("market-price", MARKET_PRICE_HELP)
        ep2 = parse_help("onchain-sql", ONCHAIN_SQL_HELP)
        generate_typescript([ep1, ep2], tmp_path)
        content = (tmp_path / "client.ts").read_text()
        assert "fetchMarketPrice" in content
        assert "fetchOnchainSql" in content


# ---------------------------------------------------------------------------
# Python generation
# ---------------------------------------------------------------------------


class TestGeneratePython:
    def test_generates_files(self, tmp_path):
        ep = parse_help("market-price", MARKET_PRICE_HELP)
        files = generate_python([ep], tmp_path)
        assert "types.py" in files
        assert "client.py" in files
        assert "__init__.py" in files

    def test_types_content(self, tmp_path):
        ep = parse_help("market-price", MARKET_PRICE_HELP)
        generate_python([ep], tmp_path)
        content = (tmp_path / "types.py").read_text()
        assert "class MarketPriceItem" in content
        assert "timestamp: int" in content
        assert "value: float" in content

    def test_client_content(self, tmp_path):
        ep = parse_help("market-price", MARKET_PRICE_HELP)
        generate_python([ep], tmp_path)
        content = (tmp_path / "client.py").read_text()
        assert "class SurfClient" in content
        assert "fetch_market_price" in content
        assert "/market/price" in content

    def test_gateway_url_env_var(self, tmp_path):
        ep = parse_help("market-price", MARKET_PRICE_HELP)
        generate_python([ep], tmp_path)
        content = (tmp_path / "client.py").read_text()
        assert "os.environ.get('SURF_BASE_URL'" in content
        assert "api.ask.surf/gateway/v1" in content

    def test_reserved_words(self, tmp_path):
        ep = parse_help("market-price", MARKET_PRICE_HELP)
        generate_python([ep], tmp_path)
        content = (tmp_path / "client.py").read_text()
        assert "from_:" in content  # 'from' renamed to 'from_'
        assert "to_:" in content
        assert "params['from'] = from_" in content

    def test_pagination_helpers(self, tmp_path):
        ep = parse_help("market-price", MARKET_PRICE_HELP)
        generate_python([ep], tmp_path)
        content = (tmp_path / "client.py").read_text()
        assert "fetch_all_pages" in content
        assert "fetch_all_cursor" in content

    def test_valid_python_syntax(self, tmp_path):
        ep = parse_help("market-price", MARKET_PRICE_HELP)
        generate_python([ep], tmp_path)
        # Compile the files to check syntax.
        for f in ["types.py", "client.py", "__init__.py"]:
            content = (tmp_path / f).read_text()
            compile(content, f, "exec")  # Raises SyntaxError if invalid.

    def test_post_endpoint(self, tmp_path):
        ep = parse_help("onchain-sql", ONCHAIN_SQL_HELP)
        generate_python([ep], tmp_path)
        content = (tmp_path / "client.py").read_text()
        assert "fetch_onchain_sql" in content
        assert "self._client.post" in content
        assert "json=body" in content
        # Required param should not have default.
        assert "sql: str" in content
        # Verify syntax.
        compile(content, "client.py", "exec")

    def test_cursor_endpoint(self, tmp_path):
        ep = parse_help("social-user-posts", SOCIAL_USER_POSTS_HELP)
        generate_python([ep], tmp_path)
        types_content = (tmp_path / "types.py").read_text()
        client_content = (tmp_path / "client.py").read_text()
        # Types should have nested author dataclass.
        assert "class SocialUserPostsItem" in types_content
        assert "class SocialUserPostsItemAuthor" in types_content
        # Client should have cursor param.
        assert "fetch_social_user_posts" in client_content
        assert "cursor" in client_content
        # Verify syntax.
        compile(types_content, "types.py", "exec")
        compile(client_content, "client.py", "exec")

    def test_object_response(self, tmp_path):
        help_text = """Get wallet detail.
## Option Schema:
```schema
{
  --address: (string) Wallet address
}
```

## Response 200 (application/json)

OK

```schema
{
  data*: {
    total_usd*: (number format:double) Total
    labels: {
      entity_name: (string) Entity name
    }
  }
  meta*: {
    cached*: (boolean) Cached
    credits_used*: (integer format:int64) Credits
  }
}
```

Usage:
  surf surf wallet-detail [flags]
"""
        ep = parse_help("wallet-detail", help_text)
        generate_python([ep], tmp_path)
        types_content = (tmp_path / "types.py").read_text()
        assert "class WalletDetailData" in types_content
        assert "total_usd: float" in types_content
        compile(types_content, "types.py", "exec")

    def test_dynamic_keys(self, tmp_path):
        """onchain-sql has <any>: <any> in response — should produce empty dataclass with pass."""
        ep = parse_help("onchain-sql", ONCHAIN_SQL_HELP)
        generate_python([ep], tmp_path)
        types_content = (tmp_path / "types.py").read_text()
        assert "class OnchainSqlItem" in types_content
        assert "pass" in types_content  # Empty dataclass from dynamic keys.
        compile(types_content, "types.py", "exec")

    def test_multiple_endpoints(self, tmp_path):
        ep1 = parse_help("market-price", MARKET_PRICE_HELP)
        ep2 = parse_help("social-user-posts", SOCIAL_USER_POSTS_HELP)
        generate_python([ep1, ep2], tmp_path)
        types_content = (tmp_path / "types.py").read_text()
        client_content = (tmp_path / "client.py").read_text()
        assert "class MarketPriceItem" in types_content
        assert "class SocialUserPostsItem" in types_content
        assert "fetch_market_price" in client_content
        assert "fetch_social_user_posts" in client_content
        compile(types_content, "types.py", "exec")
        compile(client_content, "client.py", "exec")


# ---------------------------------------------------------------------------
# Integration: real surf CLI (skip if not available)
# ---------------------------------------------------------------------------


@pytest.fixture
def has_surf():
    result = subprocess.run(["surf", "list-operations"], capture_output=True, text=True)
    if result.returncode != 0:
        pytest.skip("surf CLI not available")
    return True


class TestIntegration:
    def test_real_market_price(self, has_surf, tmp_path):
        result = subprocess.run(["surf", "market-price", "--help"], capture_output=True, text=True)
        ep = parse_help("market-price", result.stdout or result.stderr)
        assert ep.method == "GET"
        assert ep.path == "/market/price"
        assert len(ep.data_fields) >= 2

        files = generate_typescript([ep], tmp_path, hooks=True)
        assert len(files) == 3

    def test_real_wallet_detail(self, has_surf, tmp_path):
        result = subprocess.run(["surf", "wallet-detail", "--help"], capture_output=True, text=True)
        ep = parse_help("wallet-detail", result.stdout or result.stderr)
        assert not ep.data_is_array  # Object response.
        assert len(ep.data_fields) >= 3

    def test_real_social_user_posts(self, has_surf, tmp_path):
        result = subprocess.run(["surf", "social-user-posts", "--help"], capture_output=True, text=True)
        ep = parse_help("social-user-posts", result.stdout or result.stderr)
        assert ep.pagination == "cursor"

    def test_real_python_gen(self, has_surf, tmp_path):
        result = subprocess.run(["surf", "market-price", "--help"], capture_output=True, text=True)
        ep = parse_help("market-price", result.stdout or result.stderr)
        files = generate_python([ep], tmp_path)
        assert len(files) == 3
        # Verify syntax.
        for f in files:
            content = (tmp_path / f).read_text()
            compile(content, f, "exec")
