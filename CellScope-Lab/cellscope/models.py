"""Independent baseline implementations, with optional torch neural regressors."""
from __future__ import annotations
import numpy as np

BASELINES = {"mean", "ridge"}
NEURAL = {"mlp", "cnn", "gru", "bilstm", "transformer", "rdb_attn_bilstm"}
ALL_MODELS = BASELINES | NEURAL


class MeanRegressor:
    def fit(self, x: np.ndarray, y: np.ndarray):
        self.value = float(np.mean(y))
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        return np.full(len(x), self.value, dtype=np.float32)


class RidgeRegressor:
    """Intercept-unregularized ridge, with stable SVD for rank-deficient matrices."""
    def __init__(self, alpha: float = 1.0):
        if alpha < 0:
            raise ValueError("alpha must be nonnegative")
        self.alpha = alpha

    def fit(self, x: np.ndarray, y: np.ndarray):
        X = x.reshape(len(x), -1).astype(np.float64)
        self.xmean = X.mean(axis=0)
        self.ymean = float(np.mean(y))
        X = X - self.xmean
        U, s, Vh = np.linalg.svd(X, full_matrices=False)
        shrink = np.divide(s, s*s + self.alpha, out=np.zeros_like(s), where=(s*s + self.alpha) > 0)
        self.coef = Vh.T @ (shrink * (U.T @ (y - self.ymean)))
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        X = x.reshape(len(x), -1).astype(np.float64)
        return ((X - self.xmean) @ self.coef + self.ymean).astype(np.float32)


def create_neural_model(name: str, sequence_length: int, in_channels: int, hidden: int = 48):
    """Defer importing torch so baseline workflows are lightweight."""
    if name not in NEURAL:
        raise ValueError(f"Not a neural model: {name}")
    import math
    import torch
    from torch import nn

    class SequenceRegressor(nn.Module):
        def __init__(self):
            super().__init__()
            self.kind = name
            if name == "mlp":
                self.net = nn.Sequential(nn.Flatten(), nn.Linear(sequence_length * in_channels, hidden),
                                         nn.ReLU(), nn.Linear(hidden, 1))
            elif name == "cnn":
                self.conv = nn.Sequential(nn.Conv1d(in_channels, hidden, 3, padding=1),
                                          nn.ReLU(), nn.AdaptiveAvgPool1d(1))
                self.head = nn.Linear(hidden, 1)
            elif name == "gru":
                self.rnn = nn.GRU(in_channels, hidden, batch_first=True)
                self.head = nn.Linear(hidden, 1)
            elif name == "bilstm":
                self.rnn = nn.LSTM(in_channels, hidden, batch_first=True, bidirectional=True)
                self.head = nn.Linear(hidden * 2, 1)
            elif name == "transformer":
                self.project = nn.Linear(in_channels, hidden)
                self.encoder = nn.TransformerEncoder(
                    nn.TransformerEncoderLayer(d_model=hidden, nhead=4, dim_feedforward=hidden*2,
                                               dropout=0.0, batch_first=True), num_layers=1)
                positions = torch.arange(sequence_length, dtype=torch.float32).unsqueeze(1)
                div = torch.exp(torch.arange(0, hidden, 2, dtype=torch.float32) * (-math.log(10000.0) / hidden))
                pe = torch.zeros(1, sequence_length, hidden)
                pe[0, :, 0::2] = torch.sin(positions * div)
                pe[0, :, 1::2] = torch.cos(positions * div[:pe[0, :, 1::2].shape[1]])
                self.register_buffer("positional_encoding", pe)
                self.head = nn.Linear(hidden, 1)
            elif name == "rdb_attn_bilstm":
                self.stem = nn.Conv1d(in_channels, hidden, 1)
                self.depthwise = nn.Conv1d(hidden, hidden, 3, padding=1, groups=hidden)
                self.pointwise = nn.Conv1d(hidden, hidden, 1)
                self.bn = nn.BatchNorm1d(hidden)
                self.relu = nn.ReLU()
                self.rnn = nn.LSTM(hidden, hidden, batch_first=True, bidirectional=True)
                self.attn = nn.Linear(hidden*2, 1)
                self.head = nn.Sequential(nn.Linear(hidden*2, hidden), nn.ReLU(), nn.Linear(hidden, 1))

        def forward(self, x):
            if self.kind == "mlp":
                return self.net(x).squeeze(-1)
            if self.kind == "cnn":
                return self.head(self.conv(x.transpose(1, 2)).squeeze(-1)).squeeze(-1)
            if self.kind in {"gru", "bilstm"}:
                h, _ = self.rnn(x)
                return self.head(h[:, -1, :]).squeeze(-1)
            if self.kind == "transformer":
                h = self.project(x) + self.positional_encoding[:, :x.shape[1]]
                return self.head(self.encoder(h).mean(dim=1)).squeeze(-1)
            if self.kind == "rdb_attn_bilstm":
                initial = self.stem(x.transpose(1, 2))
                h = self.relu(self.bn(self.pointwise(self.depthwise(initial))) + initial)
                h, _ = self.rnn(h.transpose(1, 2))
                weights = torch.softmax(self.attn(h).squeeze(-1), dim=1).unsqueeze(-1)
                return self.head((h * weights).sum(dim=1)).squeeze(-1)
            raise RuntimeError("Unknown architecture")
    return SequenceRegressor()


def train_neural(name, train_x, train_y, val_x, val_y, *, seed=42, epochs=12,
                 lr=0.001, hidden=48, batch_size=128, shuffle=False):
    import copy
    import torch
    torch.manual_seed(seed)
    torch.set_num_threads(min(2, torch.get_num_threads()))
    model = create_neural_model(name, train_x.shape[1], train_x.shape[2], hidden)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    data = torch.utils.data.TensorDataset(torch.from_numpy(train_x), torch.from_numpy(train_y))
    loader = torch.utils.data.DataLoader(data, batch_size=batch_size, shuffle=shuffle)
    valid_x = torch.from_numpy(val_x)
    valid_y = torch.from_numpy(val_y)
    best_loss, best_state, best_epoch = float("inf"), None, -1
    history = []
    for epoch in range(epochs):
        model.train()
        losses = []
        for bx, by in loader:
            opt.zero_grad()
            loss = torch.mean((model(bx) - by)**2)
            loss.backward()
            opt.step()
            losses.append((float(loss.detach()), len(bx)))
        model.eval()
        with torch.no_grad():
            val_loss = float(torch.mean((model(valid_x)-valid_y)**2))
        train_loss = sum(v*n for v, n in losses)/sum(n for _, n in losses)
        history.append({"epoch": epoch+1, "train_mse": train_loss, "val_mse": val_loss})
        if val_loss < best_loss:
            best_loss, best_state, best_epoch = val_loss, copy.deepcopy(model.state_dict()), epoch+1
    model.load_state_dict(best_state)
    model.eval()
    return model, history, best_epoch


def predict_neural(model, x):
    import torch
    with torch.no_grad():
        return model(torch.from_numpy(x)).cpu().numpy().astype(np.float32)
