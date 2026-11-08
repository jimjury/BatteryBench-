# CellScope Lab

**An original, auditable Battery AI workbench — from data provenance to SOC / SOH / RUL model diagnostics.**

[简体中文](README.zh-CN.md) · [Research protocols](docs/DATA_PROTOCOL.md) · [Architecture](docs/ARCHITECTURE.md) · [Source attribution](docs/REFERENCES.md) · [QA status](docs/QA.md)

> **Status: functional research prototype (v0.1.0).** Unlike a paper benchmark, this project does not claim validated performance on BatteryBench or BatteryLife raw datasets. It does not contain their model code or redistribute their data. The bundled result is a real run on transparently **synthetic** data.

## What makes CellScope Lab different?

BatteryBench emphasizes shared SOH/RUL evaluation tasks and domain generalization; BatteryLife emphasizes standardized battery-lifetime data and open baselines. **CellScope Lab bridges methods and education** through an interactive model observatory, a provenance-aware dataset catalog, strict group split audits, an executable minimal Python engine, and importable evidence reports. The backend and website code in this repository were independently implemented.

| Capability | Current implementation |
|---|---|
| Research tasks | SOC next-timestep regression, current-cycle SOH regression, current-cycle RUL regression |
| Baseline / neural models | Mean, Ridge, MLP, Conv1D, GRU, BiLSTM, TransformerEncoder, RDB-Attn-BiLSTM |
| Native data protocol | Canonical CSV + common `V/I/T/SOC` aliases, cell / cycle ID required |
| Processing | Finite-value checks, duplicate time detection, phase selection, row decimation, gap-aware windows |
| Fair evaluation | Grouped train/validation/test, train-only normalizers (standard, minmax, none), validation-selected neural epoch |
| Results | RMSE, MAE, R², safe MAPE, test-cell metrics, low-SOC metrics, predictions and provenance JSON |
| Web interface | Offline-capable static HTML with dataset search, signal simulator, split inspector, 8 animated model blueprints, config export, JSON result viewer |
| Data catalog | 12 source/protocol cards, each linked to an external origin; **no downloaded dataset is bundled** |

### Quick start (Python 3.10+)

```bash
python -m pip install -e .
python -m cellscope demo --out examples/generated/synthetic.csv
python -m cellscope inspect --data examples/generated/synthetic.csv --task soc
python -m cellscope train --config configs/soc_demo.json --out runs/soc_demo
python -m cellscope train --config configs/soh_demo.json --out runs/soh_demo
python -m cellscope train --config configs/rul_demo.json --out runs/rul_demo
```

The **default `ridge` experiment requires only NumPy and pandas**. For neural models:

```bash
python -m pip install -e '.[neural]'
# Edit "model" to "rdb_attn_bilstm", "cnn", "gru", etc. in a config file.
python -m cellscope train --config configs/soc_demo.json --out runs/neural_01
```

A training run generates `metrics.json`, `config.json` and `predictions_{train,val,test}.csv`; a neural run additionally generates `weights.pt`. Training uses validation labels to select the epoch and never uses test labels for weight/epoch selection.

### Open the HTML laboratory

Either open `web/index.html` directly in a browser (classic JavaScript, no build step), or serve it locally:

```bash
python -m http.server 8000
# http://localhost:8000/web/
```

The HTML is a **visual control plane, not a browser ML trainer**. Its architectural animations show **illustrative dataflow**, not live neural activations. The data explorer points to external sources. Experiment JSON is generated in the browser, then executed with the Python CLI on real or synthetic CSV data. `metrics.json` can be imported into the results page; files remain local to the browser.

### Data contract

Supply one **canonical CSV**, not a pickle or untrusted checkpoint, with `cell_id,cycle_index,time_s,voltage_v,current_a,temperature_c` and one target `soc` / `soh` / `rul_cycles` for your chosen task. Use `cellscope prepare` to normalize common column aliases and export a cleaned file. See [full contract](docs/DATA_PROTOCOL.md).

SOC uses **exactly V/I/T** inputs: `[B, W, 3]` at times *t−W..t−1*, label `SOC(t)` at the **next** time step. A held-out cell/cycle is never crossed when building a window. SOH/RUL use previous `W` cycle summaries with five **non-capacity** measurement statistics; their label is from the current final cycle in the window. We intentionally do not infer RUL from the last recorded row or invent SOC/SOH ground truth from missing metadata.

The default split is **battery-level** with a fixed seed. The optional cycle-level split exists only for SOC where cross-battery claims are not made. SOH/RUL trajectory tasks refuse cycle-level splits to avoid history leakage. Normalization parameters are fitted on training windows only and reused unmodified for validation/test; min-max held-out values can lie outside `[0,1]`.

### Testing

```bash
python -m pip install -e '.[test,neural]'
python -m pytest -q
node --test tests-js/*.cjs
python scripts/verify_assets.py
# Optional if Chromium/Playwright browser navigation is permitted:
python tests/browser_smoke.py
```

All tasks and baseline demos were executed locally during project creation. For exact test coverage and environment limitations see [QA status](docs/QA.md).

## Project map

```text
cellscope/       ingestion, splits, causal features, 8 models, training, evaluation, CLI
configs/         executable SOC / SOH / RUL experiments
web/             portable static UI; data/catalog.json is the source of truth
scripts/         embeds JSON as classic scripts for offline file:// use; verifies assets
tests/           Python correctness and CLI integration tests
tests-js/        Node tests for UI numerical rules
.github/         CI + GitHub Pages deployment template
docs/            data contract, architecture, source review, QA, future work
```

## Research boundaries

- This release implements **CSV-based adapters**, not a complete import of every proprietary `.pkl`/`.mat`/`.h5` format mentioned in external repositories. Conversion must be audited dataset by dataset.
- The 12 catalog entries are **references**, not hosted, independently validated datasets. Check dataset licensing, DOI and primary-publication details at the linked source.
- No benchmark leaderboard is claimed, and the synthetic test RMSE **must not** be compared with published model performance.
- Safety fault diagnosis, physical simulations, uncertainty calibration, domain adaptation and extensive hyperparameter searches are **planned extensions**, not claimed current capabilities.
- Other authors' licenses and attribution are summarized in [REFERENCES.md](docs/REFERENCES.md). This code is an original MIT implementation, **not a copy/fork of either reference repository**.

## Inspiration & credits

- [BatteryBench](https://github.com/LMDHQ-0420/BatteryBench) — benchmark task and split-design inspiration (MIT, 2026).
- [BatteryLife](https://github.com/Ruifeng-Tan/BatteryLife) — data standardization and lifecycle experiment inspiration (MIT, 2025).
- [BatteryML](https://github.com/microsoft/BatteryML), [BEEP](https://github.com/TRI-AMDD/beep), [PyBaMM](https://github.com/pybamm-team/PyBaMM), and [BatteryDashboard](https://github.com/tum-ees/BatteryDashboard) — related ecosystem resources; no source code incorporated.

See [references and licensing notes](docs/REFERENCES.md). Cite the original dataset papers when conducting real experiments.
