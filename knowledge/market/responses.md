# Market Data — Response Formats

## Unified Response Envelope

All hermod responses use a unified envelope:

**Success:**
```json
{
  "data": T,
  "meta": {
    "credits": N
  }
}
```

**Error:**
```json
{
  "error": {
    "code": "...",
    "message": "..."
  }
}
```

No provider-specific wrappers — hermod normalizes all upstream responses into this format.

<!-- TODO: some endpoints still return model.RawJSON inside "data" — will be typed later -->

## Indicator Response Shapes

The `data` field for `/indicator` varies by indicator type:

| Indicator | Fields in `data` |
|-----------|------------------|
| `rsi`, `ma`, `ema`, `atr`, `adx`, `cci` | `{"value": N}` |
| `macd` | `{"valueMACD", "valueMACDSignal", "valueMACDHist"}` |
| `bbands` | `{"valueUpperBand", "valueMiddleBand", "valueLowerBand"}` |
| `stoch` | `{"valueK", "valueD"}` |

## Market Indicator Field Names

The `/market-indicator` endpoint returns metric-specific field names:
- SOPR: `sopr`, `a_sopr`, `sth_sopr`, `lth_sopr`
- MVRV: `mvrv`
- Netflow: `netflow_total`
