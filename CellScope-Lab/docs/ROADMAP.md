# Roadmap (not a list of completed features)

## V0.1 delivered

- Three supervised tasks, canonical CSV, audited cleaning, no-interpolation row sampling, gap-aware windows.
- Eight runnable models; fixed grouped split and train-only normalization; result JSON with provenance.
- 12 source/protocol cards, interactive web signal laboratory, split audit and dynamic model explorer.
- Pure static HTML with local result upload; Python/Node automated tests.

## V0.2 proposed, NOT implemented

- Independently verified dataset-specific adapters for BatteryLife standardized artifacts and selected BatteryBench raw datasets, with validation fixtures.
- Explicit train/validation/test source manifests, cross-profile holdouts, leave-one-cell-out evaluation, duplicate sample fingerprints.
- Real model-activation/attention visualization imported from instrumented PyTorch runs, rather than schematic animation.
- Uncertainty intervals with calibrated coverage and per-SOC / per-temperature error slices.
- Experiment registry, HTML exportable reports, multi-seed summary and paired statistical comparison.

## V0.3 exploration, NOT implemented

- Dedicated health and diagnostic model families, fault early warning only when labels and safety evaluation protocols support it.
- Physics-engine optional integration with PyBaMM under its own license and reproducibility controls.
- Rich plugin adapters, task-specific provenance certificates and generalization protocol cards.

Changes should be evaluated on data integrity, practical model utility, reproducibility and performance rather than feature counts alone.
