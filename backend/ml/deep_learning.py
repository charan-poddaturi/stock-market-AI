"""
Deep Learning Models: LSTM, GRU, CNN+LSTM, Transformer, N-BEATS
Built with PyTorch for time-series prediction.
"""
import os
import logging
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from typing import Tuple, Optional, Dict
from config import settings

logger = logging.getLogger(__name__)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"DL using device: {DEVICE}")

MODEL_DIR = "models/saved"

# In-memory cache for loaded models to avoid repeated disk I/O
_DL_MODEL_CACHE: dict = {}


# ─── Dataset ──────────────────────────────────────────────────────────────────
class TimeSeriesDataset(Dataset):
    def __init__(self, X: np.ndarray, y: np.ndarray):
        self.X = torch.FloatTensor(X)
        self.y = torch.FloatTensor(y)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


# ─── LSTM Model ───────────────────────────────────────────────────────────────
class LSTMModel(nn.Module):
    def __init__(self, input_size: int, hidden_size: int = 128, num_layers: int = 2, dropout: float = 0.3):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size, hidden_size, num_layers,
            batch_first=True, dropout=dropout, bidirectional=True
        )
        self.attention = nn.Linear(hidden_size * 2, 1)
        self.fc = nn.Sequential(
            nn.Linear(hidden_size * 2, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        out, _ = self.lstm(x)
        attn_weights = torch.softmax(self.attention(out), dim=1)
        context = (attn_weights * out).sum(dim=1)
        return self.fc(context).squeeze(-1)


# ─── GRU Model ────────────────────────────────────────────────────────────────
class GRUModel(nn.Module):
    def __init__(self, input_size: int, hidden_size: int = 128, num_layers: int = 2, dropout: float = 0.3):
        super().__init__()
        self.gru = nn.GRU(
            input_size, hidden_size, num_layers,
            batch_first=True, dropout=dropout
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        out, _ = self.gru(x)
        return self.fc(out[:, -1, :]).squeeze(-1)


# ─── CNN-LSTM Model ───────────────────────────────────────────────────────────
class CNNLSTMModel(nn.Module):
    def __init__(self, input_size: int, num_filters: int = 64, lstm_hidden: int = 128, dropout: float = 0.3):
        super().__init__()
        self.cnn = nn.Sequential(
            nn.Conv1d(input_size, num_filters, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv1d(num_filters, num_filters, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        self.lstm = nn.LSTM(num_filters, lstm_hidden, batch_first=True)
        self.fc = nn.Sequential(
            nn.Linear(lstm_hidden, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        # x: (batch, seq, features) -> CNN expects (batch, features, seq)
        x = x.permute(0, 2, 1)
        x = self.cnn(x)
        x = x.permute(0, 2, 1)  # Back to (batch, seq, filters)
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :]).squeeze(-1)


# ─── Transformer Model ────────────────────────────────────────────────────────
class TransformerModel(nn.Module):
    def __init__(self, input_size: int, d_model: int = 64, nhead: int = 4, num_layers: int = 2,
                 dropout: float = 0.2, seq_len: int = 60):
        super().__init__()
        self.input_proj = nn.Linear(input_size, d_model)
        self.pos_embedding = nn.Embedding(seq_len + 1, d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dropout=dropout, batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.fc = nn.Sequential(
            nn.Linear(d_model, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        b, seq, _ = x.shape
        x = self.input_proj(x)
        positions = torch.arange(seq, device=x.device).unsqueeze(0).expand(b, -1)
        x = x + self.pos_embedding(positions)
        x = self.transformer(x)
        return self.fc(x[:, -1, :]).squeeze(-1)


# ─── N-BEATS ─────────────────────────────────────────────────────────────────
class NBEATSBlock(nn.Module):
    def __init__(self, in_features: int, hidden: int = 256, basis_size: int = 32):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(in_features, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
        )
        self.backcast = nn.Linear(hidden, in_features)
        self.forecast = nn.Linear(hidden, basis_size)

    def forward(self, x):
        x_flat = x.reshape(x.size(0), -1)
        h = self.fc(x_flat)
        return self.backcast(h), self.forecast(h)


class NBEATSModel(nn.Module):
    def __init__(self, input_size: int, seq_len: int = 60, num_blocks: int = 3):
        super().__init__()
        self.blocks = nn.ModuleList([
            NBEATSBlock(input_size * seq_len, basis_size=32) for _ in range(num_blocks)
        ])
        self.forecast_head = nn.Sequential(
            nn.Linear(32 * num_blocks, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        forecasts = []
        residual = x.reshape(x.size(0), -1)
        for block in self.blocks:
            backcast, forecast = block(residual.reshape(x.size(0), x.size(1), -1))
            residual = residual - backcast
            forecasts.append(forecast)
        combined = torch.cat(forecasts, dim=-1)
        return self.forecast_head(combined).squeeze(-1)


# ─── Training ─────────────────────────────────────────────────────────────────
def train_model(
    model: nn.Module,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    epochs: int = 50,
    batch_size: int = 32,
    lr: float = 1e-3,
    patience: int = 10,
) -> Dict[str, list]:
    model = model.to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)
    criterion = nn.BCELoss()

    train_ds = TimeSeriesDataset(X_train, y_train)
    val_ds = TimeSeriesDataset(X_val, y_val)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=False)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    history = {"train_loss": [], "val_loss": [], "val_acc": []}
    best_val_loss = float("inf")
    patience_counter = 0

    for epoch in range(epochs):
        model.train()
        train_losses = []
        for xb, yb in train_loader:
            xb, yb = xb.to(DEVICE), yb.to(DEVICE)
            optimizer.zero_grad()
            out = model(xb)
            loss = criterion(out, yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_losses.append(loss.item())

        model.eval()
        val_losses, correct, total = [], 0, 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(DEVICE), yb.to(DEVICE)
                out = model(xb)
                val_losses.append(criterion(out, yb).item())
                preds = (out > 0.5).float()
                correct += (preds == yb).sum().item()
                total += len(yb)

        train_loss = np.mean(train_losses)
        val_loss = np.mean(val_losses)
        val_acc = correct / max(total, 1)
        scheduler.step(val_loss)

        history["train_loss"].append(round(train_loss, 6))
        history["val_loss"].append(round(val_loss, 6))
        history["val_acc"].append(round(val_acc, 4))

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"Early stopping at epoch {epoch+1}")
                break

    return history


def predict_model(
    model: nn.Module,
    X: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """Returns (predictions, probabilities)."""
    model = model.to(DEVICE)
    model.eval()
    with torch.no_grad():
        xb = torch.FloatTensor(X).to(DEVICE)
        probs = model(xb).cpu().numpy()
        preds = (probs > 0.5).astype(int)
    return preds, probs


def save_model(model: nn.Module, ticker: str, model_name: str):
    os.makedirs(MODEL_DIR, exist_ok=True)
    path = os.path.join(MODEL_DIR, f"{ticker}_{model_name}.pt")
    torch.save(model.state_dict(), path)
    logger.info(f"Saved {model_name} for {ticker}")


def load_model(model: nn.Module, ticker: str, model_name: str) -> Optional[nn.Module]:
    path = os.path.join(MODEL_DIR, f"{ticker}_{model_name}.pt")
    if not os.path.exists(path):
        return None

    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None

    cache_entry = _DL_MODEL_CACHE.get(path)
    if cache_entry and cache_entry.get("mtime") == mtime:
        return cache_entry.get("model")

    model.load_state_dict(torch.load(path, map_location=DEVICE))
    model.eval()
    _DL_MODEL_CACHE[path] = {"model": model, "mtime": mtime}
    return model


def build_model(model_name: str, input_size: int, seq_len: int = 60) -> nn.Module:
    """Factory function to create model by name."""
    models = {
        "lstm": LSTMModel(input_size=input_size),
        "gru": GRUModel(input_size=input_size),
        "cnn_lstm": CNNLSTMModel(input_size=input_size),
        "transformer": TransformerModel(input_size=input_size, seq_len=seq_len),
        "nbeats": NBEATSModel(input_size=input_size, seq_len=seq_len),
    }
    return models.get(model_name, LSTMModel(input_size=input_size))
