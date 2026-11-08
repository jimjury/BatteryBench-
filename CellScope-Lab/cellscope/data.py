"""Canonical CSV ingestion with explicit, inspectable loss of rows.

No interpolations, capacity-derived labels, or silent battery-id fabrication.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd

ALIASES = {
    "cell_id": ["battery_id", "cell", "Cell_ID", "Battery_ID"],
    "cycle_index": ["cycle", "Cycle", "cycle_number", "Cycle_Index"],
    "time_s": ["time", "Time", "time_in_s", "Time_s"],
    "voltage_v": ["Voltage_V", "Voltage", "voltage_in_V", "voltage"],
    "current_a": ["Current_A", "Current", "current_in_A", "current"],
    "temperature_c": ["T", "Temperature", "Battery_Temp_degC", "temperature_in_C"],
    "soc": ["SOC", "SoC", "state_of_charge"],
    "soh": ["SOH", "SoH", "state_of_health"],
    "rul_cycles": ["RUL", "rul", "remaining_life", "remaining_cycles"],
    "condition": ["Condition", "profile", "drive_cycle"],
}
BASE_COLUMNS = ["cell_id", "cycle_index", "time_s", "voltage_v", "current_a", "temperature_c"]
TARGET_COLUMNS = {"soc": "soc", "soh": "soh", "rul": "rul_cycles"}


@dataclass
class Ingestion:
    frame: pd.DataFrame
    report: dict


def canonical_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Rename known aliases, refusing ambiguous canonical+alias collisions."""
    cols = set(frame.columns)
    rename = {}
    for canonical, aliases in ALIASES.items():
        found = [c for c in [canonical, *aliases] if c in cols]
        if len(found) > 1:
            raise ValueError(f"Ambiguous columns for {canonical}: {found}")
        if found and found[0] != canonical:
            rename[found[0]] = canonical
    return frame.rename(columns=rename)


def load_csv(path: str | Path, *, task: str = "soc", phase: str = "discharge",
             discharge_sign: str = "negative", decimation_step: int = 1,
             current_tol: float = 1e-9, max_gap_sec: float = 10.0) -> Ingestion:
    if task not in TARGET_COLUMNS:
        raise ValueError(f"Unknown task {task!r}; expected soc, soh, or rul")
    if phase not in {"all", "discharge"}:
        raise ValueError("phase must be 'all' or 'discharge'")
    if discharge_sign not in {"positive", "negative"}:
        raise ValueError("discharge_sign must be positive or negative")
    if not isinstance(decimation_step, int) or decimation_step < 1:
        raise ValueError("decimation_step must be an integer >= 1")
    if max_gap_sec <= 0:
        raise ValueError("max_gap_sec must be > 0")
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    df = canonical_columns(pd.read_csv(source, low_memory=False))
    target = TARGET_COLUMNS[task]
    required = BASE_COLUMNS + [target]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}. See docs/DATA_PROTOCOL.md")
    initial = len(df)
    df = df.dropna(subset=["cell_id"]).copy()
    df["cell_id"] = df["cell_id"].astype(str).str.strip()
    df = df[df["cell_id"] != ""]
    for col in required:
        if col != "cell_id":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    finite_cols = [c for c in required if c != "cell_id"]
    good = np.isfinite(df[finite_cols].to_numpy(dtype=float)).all(axis=1)
    df = df.loc[good].copy()
    nonnumeric_removed = initial - len(df)
    if len(df) == 0:
        raise ValueError("No finite numeric data after cleaning")
    if not np.equal(df["cycle_index"], np.floor(df["cycle_index"])).all():
        raise ValueError("cycle_index must have integer values")
    df["cycle_index"] = df["cycle_index"].astype(int)
    dup_n = int(df.duplicated(["cell_id", "cycle_index", "time_s"]).sum())
    df = df.drop_duplicates(["cell_id", "cycle_index", "time_s"], keep="first")
    if phase == "discharge":
        active = df["current_a"] < -current_tol if discharge_sign == "negative" else df["current_a"] > current_tol
        df = df.loc[active].copy()
    filtered_n = initial - nonnumeric_removed - dup_n - len(df)
    if df.empty:
        raise ValueError("No samples remain after phase selection; check current sign")
    df = df.sort_values(["cell_id", "cycle_index", "time_s"], kind="stable")
    if decimation_step > 1:
        df = df.groupby(["cell_id", "cycle_index"], sort=False, group_keys=False).nth(
            list(range(0, int(df.groupby(["cell_id", "cycle_index"]).size().max()), decimation_step))
        )
        # 'nth' retains original row indexes and the original group columns.
        df = df.sort_values(["cell_id", "cycle_index", "time_s"], kind="stable")
    else:
        df = df.copy()
    gap_counts = 0
    for (_, _), g in df.groupby(["cell_id", "cycle_index"], sort=False):
        gap_counts += int(np.sum(np.diff(g["time_s"].to_numpy()) > max_gap_sec))
    report = {
        "input_rows": int(initial), "invalid_rows": int(nonnumeric_removed),
        "duplicate_timestamps": dup_n, "phase_filtered_rows": int(filtered_n),
        "output_rows": int(len(df)), "cells": int(df["cell_id"].nunique()),
        "cycles": int(df.groupby(["cell_id", "cycle_index"]).ngroups),
        "gaps_above_limit": gap_counts,
        "decimation_step": int(decimation_step), "interpolated_rows": 0,
        "notes": "Row decimation is not necessarily 1 Hz; verify source cadence. No interpolation performed.",
    }
    if task == "soc" and not df["soc"].between(0, 1).all():
        raise ValueError("SOC label must be a fraction in [0,1], not a percentage")
    if task == "soh" and not df["soh"].between(0, 1.5).all():
        raise ValueError("SOH label must be a fraction, plausibly in [0,1.5]")
    if task == "rul" and (df["rul_cycles"] < 0).any():
        raise ValueError("RUL label must be nonnegative; exclude censored cells without an observed EOL")
    return Ingestion(df.reset_index(drop=True), report)
