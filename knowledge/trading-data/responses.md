# Trading Data — Response Formats

<!-- TODO: will be updated after hermod refactor -->

## Wrapper Format Cheat Sheet

| Provider | Wrapper | Success Check |
|----------|---------|---------------|
| CoinGlass | `{"code": "0", "data": [...]}` | `code == "0"` (**string**) |
| CryptoQuant | `{"status": {"code": 200}, "result": {"data": [...]}}` | `status.code == 200` (int) |
| SoSoValue | `{"code": 0, "data": {...}}` | `code == 0` (int), values are **strings** |
| CoinGecko | Raw JSON, no wrapper | HTTP status |
| TAAPI | Raw JSON, no wrapper | HTTP status |

## Indicator Response Shapes

| Indicator | Fields |
|-----------|--------|
| `rsi`, `ma`, `ema`, `atr`, `adx`, `cci` | `{"value": N}` |
| `macd` | `{"valueMACD", "valueMACDSignal", "valueMACDHist"}` |
| `bbands` | `{"valueUpperBand", "valueMiddleBand", "valueLowerBand"}` |
| `stoch` | `{"valueK", "valueD"}` |

## CryptoQuant Field Names

Response field is the metric name itself, NOT a generic `value`:
- SOPR → `sopr`, `a_sopr`, `sth_sopr`, `lth_sopr`
- MVRV → `mvrv`
- Netflow → `netflow_total`

## SoSoValue Notes

- All values are strings, parse with `float()`
- `status`: `"1"` = current, `"2"` = prev day, `"3"` = unavailable (null)
- Individual fund `dailyNetInflow` can be null when aggregate exists
