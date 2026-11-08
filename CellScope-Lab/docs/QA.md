# Verification summary

**Checked at initial delivery (2026-11-08):**

- Python unit and integration suite: **13 tests passed** for alias handling, phase filtering, row decimation, gap-aware future-safe target alignment, deterministic splits, train-only normalization, metric handling, supervised tasks and neural model forward passes.
- Node native test suite: **6 tests passed** for deterministic split math, cycle-overlap warning, simulation counts, configuration validation, bundled real CLI report schema and catalog links.
- Python CLI end-to-end smoke: synthetic data generation + three Ridge tasks executed; report JSON, prediction CSVs, audit fields produced. Neural architecture forward-shape checks ran for six available PyTorch variants. A separate 2-epoch CPU training smoke test also successfully trained the residual-convolution + single-head attention + BiLSTM model, selected a validation epoch, and saved weights. This is a pipeline check, **not** a claim of scientific accuracy.
- HTML static checks: unique DOM element IDs, local script references and JavaScript syntax validated. Asset synchronization script checks generated JS against JSON originals.

**Not verified:** browser-level click/resize screenshots. The execution environment has an administrator-managed Chromium URL blocklist (`*`) that prevents both `file://` and local HTTP navigation, even through Playwright. `tests/browser_smoke.py` contains interaction checks for all major controls and two responsive viewports, uses the included example report, and can be executed in an unrestricted environment. Until this is run, browser pixel layout and keyboard interaction are **not fully certified**.

**Additional limitations:** public raw dataset downloads, scientific adapter equivalence, paper figure/metric replication, GPU throughput and GitHub Pages deployment are not independently validated in this release.

## Suggested reproducibility commands

```bash
python -m pip install -e '.[test,neural]'
python -m pytest -q
node --test tests-js/*.cjs
python scripts/verify_assets.py
python -m cellscope demo --out examples/generated/synthetic.csv
python -m cellscope train --config configs/soc_demo.json --out runs/soc_demo
python tests/browser_smoke.py  # only if an unrestricted Chrome/Chromium is available
```

For real studies, add dataset-specific QC fixtures and at least two independent data-processing checks before publishing benchmarks.
