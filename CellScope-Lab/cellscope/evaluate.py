"""Scalar regression metrics with explicit safe handling of near-zero targets."""
from __future__ import annotations
import numpy as np


def scores(y, pred):
    y = np.asarray(y, dtype=float)
    pred = np.asarray(pred, dtype=float)
    if y.shape != pred.shape or y.ndim != 1:
        raise ValueError("Prediction and label vectors must have matching shape")
    if len(y) == 0:
        return None
    err = pred-y
    denominator = float(np.sum((y - y.mean())**2))
    valid_pct = np.abs(y) >= 1e-3
    return {
        "n": int(len(y)),
        "rmse": float(np.sqrt(np.mean(err*err))),
        "mae": float(np.mean(np.abs(err))),
        "r2": float(1 - np.sum(err*err)/denominator) if denominator > 1e-12 else None,
        "mape_percent": float(100*np.mean(np.abs(err[valid_pct]/y[valid_pct]))) if valid_pct.any() else None,
        "mape_eligible": int(valid_pct.sum()),
    }


def by_cell(cells, y, pred):
    return {cell: scores(y[np.asarray(cells)==cell], pred[np.asarray(cells)==cell])
            for cell in sorted(set(cells))}


def low_soc(y, pred, threshold=0.20):
    eligible = np.asarray(y) <= threshold
    return {"threshold": float(threshold), "metrics": scores(np.asarray(y)[eligible], np.asarray(pred)[eligible])}
