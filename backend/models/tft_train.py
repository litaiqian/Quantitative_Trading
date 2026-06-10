"""
Temporal Fusion Transformer (TFT) 简化实现
用于时间序列预测，与 XGBoost 互补
"""

import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

MODEL_DIR = Path(__file__).parent / "saved"
MODEL_DIR.mkdir(exist_ok=True)


class TFTModel(nn.Module):
    """简化版 TFT — LSTM + Attention，适合 K 线序列"""

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 128,
        num_layers: int = 2,
        seq_len: int = 60,
        num_classes: int = 3,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.seq_len = seq_len
        self.input_proj = nn.Linear(input_dim, hidden_dim)

        # LSTM 编码器
        self.lstm = nn.LSTM(
            hidden_dim, hidden_dim, num_layers, batch_first=True, dropout=dropout
        )

        # Multi-head 自注意力
        self.attention = nn.MultiheadAttention(
            hidden_dim, num_heads=4, batch_first=True, dropout=dropout
        )

        # 门控残差
        self.gate = nn.Linear(hidden_dim * 2, hidden_dim)
        self.gate_norm = nn.LayerNorm(hidden_dim)

        # 输出头
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes),
        )

    def forward(self, x):
        # x: (batch, seq_len, features)
        x = self.input_proj(x)

        lstm_out, _ = self.lstm(x)
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)

        # 门控融合
        combined = torch.cat([lstm_out, attn_out], dim=-1)
        gate = torch.sigmoid(self.gate(combined))
        fused = self.gate_norm(gate * lstm_out + (1 - gate) * attn_out)

        # 取最后一个时间步
        last = fused[:, -1, :]
        return self.fc(last)


def build_sequences(
    df: pd.DataFrame, feature_cols: list, seq_len: int = 60
) -> tuple:
    """从 DataFrame 构建序列样本"""
    X_data = df[feature_cols].values
    y_data = df["target_class"].values + 1  # -1,0,1 → 0,1,2

    # 标准化
    scaler = StandardScaler()
    X_data = scaler.fit_transform(X_data)

    X_seq, y_seq = [], []
    for i in range(seq_len, len(X_data) - 1):
        X_seq.append(X_data[i - seq_len : i])
        y_seq.append(y_data[i])

    X_seq = np.array(X_seq, dtype=np.float32)
    y_seq = np.array(y_seq, dtype=np.int64)

    # 80/20 分割
    split = int(len(X_seq) * 0.8)
    return X_seq[:split], X_seq[split:], y_seq[:split], y_seq[split:], scaler


def train(
    df: pd.DataFrame,
    feature_cols: list,
    symbol: str = "BTC/USDT",
    seq_len: int = 60,
    epochs: int = 50,
    batch_size: int = 64,
    save: bool = True,
):
    """训练 TFT"""
    print(f"\n{'='*50}")
    print(f"  🧠 TFT 训练 — {symbol}")
    print(f"{'='*50}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  设备: {device}")

    X_train, X_test, y_train, y_test, scaler = build_sequences(
        df, feature_cols, seq_len
    )
    print(f"  训练样本: {len(X_train)}, 测试样本: {len(X_test)}")

    train_ds = TensorDataset(
        torch.tensor(X_train), torch.tensor(y_train)
    )
    test_ds = TensorDataset(torch.tensor(X_test), torch.tensor(y_test))
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=batch_size)

    model = TFTModel(
        input_dim=len(feature_cols), seq_len=seq_len
    ).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, epochs)
    criterion = nn.CrossEntropyLoss()

    best_acc = 0
    for epoch in range(epochs):
        model.train()
        train_loss = 0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_loss += loss.item()
        scheduler.step()

        # 验证
        model.eval()
        correct, total = 0, 0
        with torch.no_grad():
            for xb, yb in test_loader:
                xb, yb = xb.to(device), yb.to(device)
                pred = model(xb).argmax(dim=1)
                correct += (pred == yb).sum().item()
                total += yb.size(0)
        acc = correct / total
        best_acc = max(best_acc, acc)

        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(
                f"  Epoch {epoch+1:3d}/{epochs}  "
                f"loss={train_loss/len(train_loader):.4f}  "
                f"acc={acc*100:.1f}%"
            )

    print(f"\n  ✅ TFT 最佳准确率: {best_acc*100:.2f}%")

    # 获取预测概率
    model.eval()
    all_proba = []
    with torch.no_grad():
        for xb, _ in test_loader:
            xb = xb.to(device)
            proba = torch.softmax(model(xb), dim=1).cpu().numpy()
            all_proba.append(proba)
    proba = np.concatenate(all_proba)

    if save:
        path = MODEL_DIR / f"tft_{symbol.replace('/', '_')}.pkl"
        with open(path, "wb") as f:
            pickle.dump(
                {"model": model, "scaler": scaler, "feature_cols": feature_cols}, f
            )
        print(f"  💾 保存模型 → {path}")

    return model, y_test, proba
