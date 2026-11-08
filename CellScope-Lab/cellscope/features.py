"""Task-specific causal windows; SOC target is the NEXT sample by design."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

SOC_INPUTS = ["voltage_v", "current_a", "temperature_c"]
CYCLE_INPUTS = ["mean_voltage", "std_voltage", "rms_current", "mean_temperature", "duration_s"]


@dataclass
class Samples:
    x: np.ndarray
    y: np.ndarray
    cells: list[str]
    feature_names: list[str]


def build_samples(frame: pd.DataFrame, *, task: str, window: int,
                  max_gap_sec: float = 10.0) -> Samples:
    if window < 1:
        raise ValueError("window must be >= 1")
    if task == "soc":
        return _soc(frame, window, max_gap_sec)
    if task in {"soh", "rul"}:
        return _health(frame, task, window, max_gap_sec)
    raise ValueError(f"Unknown task {task}")


def _soc(df: pd.DataFrame, window: int, max_gap_sec: float) -> Samples:
    x, y, cells = [], [], []
    for (cell, cycle), block in df.groupby(["cell_id", "cycle_index"], sort=True):
        g = block.sort_values("time_s")
        time = g["time_s"].to_numpy(dtype=float)
        feats = g[SOC_INPUTS].to_numpy(dtype=np.float32)
        labels = g["soc"].to_numpy(dtype=np.float32)
        segment_start = 0
        breaks = list(np.where(np.diff(time) > max_gap_sec)[0] + 1) + [len(g)]
        for segment_end in breaks:
            # Window [t, ..., t+window-1] => label[t+window]
            for end in range(segment_start + window, segment_end):
                x.append(feats[end-window:end])
                y.append(labels[end])
                cells.append(str(cell))
            segment_start = segment_end
    return _assemble(x, y, cells, window, SOC_INPUTS)


def _health(df: pd.DataFrame, task: str, window: int, max_gap_sec: float) -> Samples:
    label = "soh" if task == "soh" else "rul_cycles"
    x, y, cells = [], [], []
    for cell, cell_df in df.groupby("cell_id", sort=True):
        records = []
        for cycle, g in cell_df.groupby("cycle_index", sort=True):
            g = g.sort_values("time_s")
            time = g["time_s"].to_numpy(dtype=float)
            if np.any(np.diff(time) > max_gap_sec):
                raise ValueError(f"Large time gap in health cycle {cell} {cycle}; audit raw cycle first")
            v = g["voltage_v"].to_numpy(dtype=float)
            i = g["current_a"].to_numpy(dtype=float)
            temp = g["temperature_c"].to_numpy(dtype=float)
            target_values = g[label].to_numpy(dtype=float)
            if np.max(target_values) - np.min(target_values) > 1e-4:
                raise ValueError(f"{task.upper()} labels must be constant within each cycle: {cell} {cycle}")
            records.append((int(cycle), np.array([
                float(v.mean()), float(v.std()), float(np.sqrt((i*i).mean())),
                float(temp.mean()), float(g["time_s"].max() - g["time_s"].min()),
            ], dtype=np.float32), float(target_values[-1])))
        # A missing cycle breaks history; never pretend it is a consecutive cycle.
        segment = []
        for record in records:
            if segment and record[0] != segment[-1][0] + 1:
                _emit_health(segment, window, str(cell), x, y, cells)
                segment = []
            segment.append(record)
        _emit_health(segment, window, str(cell), x, y, cells)
    return _assemble(x, y, cells, window, CYCLE_INPUTS)


def _emit_health(segment, window, cell, x, y, cells):
    for j in range(window-1, len(segment)):
        x.append(np.stack([row[1] for row in segment[j-window+1:j+1]]))
        y.append(segment[j][2])
        cells.append(cell)


def _assemble(x, y, cells, window, names):
    if not x:
        return Samples(np.empty((0, window, len(names)), dtype=np.float32),
                       np.empty((0,), dtype=np.float32), [], list(names))
    return Samples(np.stack(x).astype(np.float32), np.asarray(y, dtype=np.float32), cells, list(names))


class Standardizer:
    def fit(self, training_x: np.ndarray) -> "Standardizer":
        if training_x.shape[0] == 0:
            raise ValueError("Cannot fit standardizer on empty training samples")
        self.mean = training_x.mean(axis=(0, 1), dtype=np.float64)
        self.std = training_x.std(axis=(0, 1), dtype=np.float64)
        self.std[self.std < 1e-9] = 1.0
        return self

    def transform(self, x: np.ndarray) -> np.ndarray:
        return ((x - self.mean) / self.std).astype(np.float32)

    def as_dict(self) -> dict:
        return {"method":"standard", "mean": self.mean.tolist(), "std": self.std.tolist(), "fit_on": "training_only"}


class MinMaxNormalizer:
    def fit(self, training_x: np.ndarray) -> "MinMaxNormalizer":
        if training_x.shape[0] == 0:
            raise ValueError("Cannot fit minmax on empty training samples")
        self.min = training_x.min(axis=(0, 1)).astype(np.float64)
        self.max = training_x.max(axis=(0, 1)).astype(np.float64)
        self.scale = self.max - self.min
        self.scale[self.scale < 1e-9] = 1.0
        return self

    def transform(self, x: np.ndarray) -> np.ndarray:
        # Held-out values may be <0 or >1; never clip silently.
        return ((x - self.min) / self.scale).astype(np.float32)

    def as_dict(self) -> dict:
        return {"method": "minmax", "min": self.min.tolist(), "max": self.max.tolist(),
                "fit_on": "training_only", "clips_test_values": False}


class IdentityNormalizer:
    def fit(self, training_x: np.ndarray) -> "IdentityNormalizer":
        if training_x.shape[0] == 0:
            raise ValueError("Cannot fit identity scaler on empty training samples")
        return self

    def transform(self, x: np.ndarray) -> np.ndarray:
        return x.astype(np.float32)

    def as_dict(self) -> dict:
        return {"method": "none", "fit_on": "not_applicable"}
