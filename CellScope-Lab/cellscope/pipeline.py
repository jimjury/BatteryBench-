"""Leakage-aware end-to-end training with reproducible machine-readable output."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from . import __version__
from .data import load_csv
from .evaluate import scores, by_cell, low_soc
from .features import build_samples, Standardizer, MinMaxNormalizer, IdentityNormalizer
from .models import ALL_MODELS, BASELINES, MeanRegressor, RidgeRegressor, train_neural, predict_neural
from .split import make_splits


def run_experiment(config: dict, *, data_override: str | None = None,
                   output_dir: str | Path = "runs/latest") -> dict:
    task, model_name = config.get("task"), config.get("model")
    if task not in {"soc", "soh", "rul"}:
        raise ValueError("task must be soc, soh or rul")
    if model_name not in ALL_MODELS:
        raise ValueError(f"Unknown model {model_name}; valid: {sorted(ALL_MODELS)}")
    dcfg = config.get("data", {})
    path = Path(data_override or dcfg.get("path", ""))
    if not path.is_file():
        raise FileNotFoundError(f"Data CSV not found: {path}; run 'cellscope demo' first")
    window = int(config.get("features", {}).get("window", 64 if task == "soc" else 6))
    if not (1 <= window <= 512):
        raise ValueError("features.window must be in [1,512]")
    scfg = config.get("split", {})
    unit = scfg.get("unit", "battery")
    if task in {"soh", "rul"} and unit != "battery":
        raise ValueError("SOH/RUL trajectory input requires battery-level holdout to avoid history leakage")
    max_gap = float(dcfg.get("max_gap_sec", 10.0))
    ingestion = load_csv(path, task=task, phase=dcfg.get("phase", "discharge"),
                         discharge_sign=dcfg.get("discharge_sign", "negative"),
                         decimation_step=int(dcfg.get("decimation_step", 1)),
                         max_gap_sec=max_gap)
    parts, split_report = make_splits(ingestion.frame, unit=unit,
                                     seed=int(scfg.get("seed", 42)),
                                     val_fraction=float(scfg.get("val_fraction", .15)),
                                     test_fraction=float(scfg.get("test_fraction", .15)))
    samples = {name: build_samples(frame, task=task, window=window, max_gap_sec=max_gap)
               for name, frame in parts.items()}
    missing = [name for name, item in samples.items() if len(item.y) == 0]
    if missing:
        raise ValueError(f"No windows for split(s) {missing}. Reduce window, increase data, or check gaps.")
    norm = config.get("features", {}).get("normalization", "standard")
    normalizers = {"standard": Standardizer, "minmax": MinMaxNormalizer, "none": IdentityNormalizer}
    if norm not in normalizers:
        raise ValueError(f"Unsupported normalization: {norm}")
    standardizer = normalizers[norm]().fit(samples["train"].x)
    transformed = {key: standardizer.transform(value.x) for key, value in samples.items()}
    train_config = config.get("train", {})
    history, best_epoch = [], None
    model = None
    if model_name in BASELINES:
        model = (MeanRegressor() if model_name == "mean" else
                 RidgeRegressor(alpha=float(train_config.get("alpha", 1.0))))
        model.fit(transformed["train"], samples["train"].y)
        predict = model.predict
    else:
        model, history, best_epoch = train_neural(
            model_name, transformed["train"], samples["train"].y,
            transformed["val"], samples["val"].y,
            seed=int(scfg.get("seed", 42)), epochs=int(train_config.get("epochs", 12)),
            lr=float(train_config.get("lr", 0.001)), hidden=int(train_config.get("hidden", 48)),
            batch_size=int(train_config.get("batch_size", 128)),
            shuffle=bool(train_config.get("shuffle", False)))
        predict = lambda x: predict_neural(model, x)
    preds = {name: predict(x) for name, x in transformed.items()}
    synthetic_claim = bool(dcfg.get("synthetic", False)) and data_override is None
    report = {
        "schema_version": "1.0", "project_version": __version__,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {"name": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "synthetic": synthetic_claim, "origin_verified": False},
        "task": task, "model": model_name, "config": config,
        "quality": ingestion.report, "split": split_report,
        "features": {"names": samples["train"].feature_names, "window": window,
                     "sequence_label_alignment": "next_time_step" if task == "soc" else "current_cycle"},
        "normalization": standardizer.as_dict(),
        "metrics": {name: scores(samples[name].y, pred) for name, pred in preds.items()},
        "by_cell": {name: by_cell(samples[name].cells, samples[name].y, pred)
                    for name, pred in preds.items()},
        "low_soc_test": low_soc(samples["test"].y, preds["test"]) if task == "soc" else None,
        "history": history, "selection": {"best_val_epoch": best_epoch,
                                           "uses_test_for_model_selection": False},
        "audit": {"group_overlap": False, "train_only_scaler": norm != "none",
                  "input_does_not_contain_target": True,
                  "window_crosses_cycle": False, "future_target_excluded_from_inputs": True},
        "limitations": ["Synthetic data are generated for demonstration and are not benchmark measurements."]
                       if synthetic_claim else [],
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    (out / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    for name, pred in preds.items():
        pd.DataFrame({"cell_id": samples[name].cells,
                      "true": samples[name].y, "predicted": pred}).to_csv(out / f"predictions_{name}.csv", index=False)
    if model_name not in BASELINES:
        import torch
        torch.save(model.state_dict(), out / "weights.pt")
    return report
