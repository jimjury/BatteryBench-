# Data protocol and leakage contract

## Canonical CSV

At minimum each row has: `cell_id`, `cycle_index` (integer), `time_s` (seconds), `voltage_v` (volts), `current_a` (amps), `temperature_c` (degrees Celsius), and **one** target column for the selected task:

- **SOC**: `soc` is a 0–1 fraction at that *row*, not a percentage.
- **SOH**: `soh` is a fraction, constant within each cycle. Definition (discharge capacity vs rated or reference capacity) must be documented in your source. This tool does **not** auto-compute SOH.
- **RUL**: `rul_cycles` is a nonnegative remaining-cycle count computed from a **known** EOL. Do not label censored cells by taking the last observed cycle as EOL.

Aliases include `Voltage_V`, `Current_A`, `T`, `SOC`, `SOH`, `Time`, `Cycle` and BatteryLife-style `voltage_in_V`, `current_in_A`, `time_in_s`, `temperature_in_C`. Ambiguous duplicate alias/canonical fields cause an error, not silent preference. `cell_id` and `cycle_index` are never fabricated.

Example:

```csv
cell_id,cycle_index,time_s,voltage_v,current_a,temperature_c,soc
C01,1,0,4.16,-1.2,25.1,1.0
C01,1,1,4.15,-1.1,25.1,0.999
C01,1,2,4.15,-1.3,25.2,0.997
```

## Cleaning policy

1. Validate required fields, finite numbers, integer cycle IDs, non-empty cell IDs and target ranges.
2. Deduplicate exact `(cell_id, cycle_index, time_s)` tuples; report count.
3. Select discharge phase by signed current (`negative` default; configurable `positive`). The current threshold is configurable in the Python API. Rest rows are removed when discharge filtering is on.
4. Stable-sort within cell and cycle; select every `decimation_step`-th **row** per cycle, starting at its first accepted row. **No interpolation.** This is 1 Hz only when source cadence and sample count justify that interpretation.
5. At sample-building time, split SOC windows at every within-cycle gap greater than `max_gap_sec`; health-cycle summaries **reject** a cycle containing such a gap. Windows never cross cell/cycle IDs or a forbidden time gap.
6. All row deletions, gaps and output counts are recorded in `quality`.

**Important limitation:** Real raw data may have step columns, CV/CC phases, resets, sensor offsets and varying clocks. This generic CSV adapter cannot infer their scientific meaning. Prepare domain-specific adapters and confirm results before making benchmark claims.

## Task alignment

| Task | Input per sample | Target | Allowed grouping |
|---|---|---|---|
| SOC | `[W,3]` ordered `[V,I,T]` rows from `t-W` through `t-1` | SOC at row `t` | Battery or cycle level |
| SOH | `[W,5]` per-cycle summaries ending at current cycle | SOH at the last cycle | Battery-level holdout |
| RUL | `[W,5]` per-cycle summaries ending at current cycle | RUL at the last cycle | Battery-level holdout |

Five *non-label* cycle features: voltage mean, voltage standard deviation, current RMS, temperature mean, elapsed discharge time. Crucially, no capacity or label-valued quantity is used as a feature. The approach is a deliberately simple benchmark, **not** a validated state-of-the-art feature extractor.

## Split and normalization

- Split **raw cell or cycle groups** first; only then build samples and fit normalization on train windows.
- Group allocation is fixed by `random.Random(seed)` over sorted identifiers. Ratios are approximate for small cell counts; group members and counts are logged.
- `standard` uses per-feature training mean/std. `minmax` uses per-feature training min/max with no clipping on held-out values. `none` leaves features unchanged.
- Normalization is fit only on the **train samples**, never on held-out labels or test features. Because overlapping windows reweight time points, this definition is exactly *per-window training sample fit*.
- The default SOC protocol predicts the **next** time point; it is not same-step classification. The user may change window length for other experiments.
- For health trajectories, cycle-level partitions are intentionally rejected because using historical cycles from other sets could leak data.
- Per-cell metrics must be interpreted alongside macro-averages; overall micro RMSE can overweight larger cells.
- MAPE excludes targets with absolute value `< 1e-3` and reports `mape_eligible`. SOC near zero must be judged using RMSE/MAE and the low-SOC slice.

## Reproduction and identity

`metrics.json` contains full split members, seed, source SHA256, normalization parameters, task, model, sample counts, metrics, sample-level predictions stored separately and audit flags. It does **not** claim a scientifically verified source license or undisclosed test calibration. Neural models use training order by default (`shuffle: false`) and choose best epoch via validation MSE.

Use `python -m cellscope prepare --data RAW.csv --task soc --out canonical.csv` to export cleaned CSV and the JSON report to stdout; `inspect` runs the same audit without writing a new CSV.

## Security

Do not load third-party pickle objects or torch checkpoints obtained from untrusted archives. The CSV interface deliberately avoids executing external deserializers. The result uploader accepts JSON and treats it as local display data; it does not execute embedded code.
