"""Disjoint group splits; normalizers must be fitted after the split."""
from __future__ import annotations
import random
import pandas as pd


def make_splits(frame: pd.DataFrame, *, unit: str = "battery", seed: int = 42,
                val_fraction: float = 0.15, test_fraction: float = 0.15) -> tuple[dict[str, pd.DataFrame], dict]:
    if unit not in {"battery", "cycle"}:
        raise ValueError("split_unit must be battery or cycle")
    if not (0 < val_fraction < 1 and 0 < test_fraction < 1 and val_fraction + test_fraction < 1):
        raise ValueError("val_fraction and test_fraction must be positive, sum less than 1")
    work = frame.copy()
    work["_split_key"] = work["cell_id"] if unit == "battery" else (
        work["cell_id"].astype(str) + "::" + work["cycle_index"].astype(str))
    keys = sorted(work["_split_key"].unique().tolist())
    if len(keys) < 3:
        raise ValueError(f"Need at least 3 independent {unit} units for train/val/test; found {len(keys)}")
    random.Random(seed).shuffle(keys)
    n_test = max(1, round(len(keys) * test_fraction))
    n_val = max(1, round(len(keys) * val_fraction))
    if n_test + n_val >= len(keys):
        n_test, n_val = 1, 1
    membership = {
        "test": sorted(keys[:n_test]),
        "val": sorted(keys[n_test:n_test + n_val]),
        "train": sorted(keys[n_test + n_val:]),
    }
    partitions = {}
    for name, subset in membership.items():
        partitions[name] = work[work["_split_key"].isin(subset)].drop(columns="_split_key").copy()
    assert not (set(membership["train"]) & set(membership["val"]))
    assert not (set(membership["train"]) & set(membership["test"]))
    assert not (set(membership["val"]) & set(membership["test"]))
    return partitions, {
        "unit": unit, "seed": int(seed), "members": membership,
        "counts": {name: len(value) for name, value in membership.items()},
        "disjoint": True,
        "warning": "Cycle-level split shares batteries across sets; not a cross-battery evaluation." if unit == "cycle" else None,
    }
