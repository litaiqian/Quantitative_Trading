"""
Stacking 集成 — 将 XGBoost + TFT 的预测概率融合
"""

import pickle
import numpy as np
import pandas as pd
from pathlib import Path
import xgboost as xgb
from sklearn.metrics import accuracy_score, classification_report

MODEL_DIR = Path(__file__).parent / "saved"


def stack_predictions(xgb_proba, tft_proba, y_true, symbol: str, save: bool = True):
    """
    用 XGBoost 做 meta-learner，融合两个模型的概率输出。
    """
    print(f"\n{'='*50}")
    print(f"  🔗 Stacking 融合 — {symbol}")
    print(f"{'='*50}")

    # 拼接两个模型的概率作为 meta 特征
    # xgb_proba: (N, 3), tft_proba: (N, 3) → meta_X: (N, 6)
    n_xgb = len(xgb_proba)
    n_tft = len(tft_proba)

    # 对齐样本数 (TFT 因 seq_len 会少一些)
    min_len = min(n_xgb, n_tft)
    xgb_aligned = xgb_proba[-min_len:]  # 取最后 min_len 个
    tft_aligned = tft_proba[-min_len:]
    y_aligned = y_true[-min_len:]

    meta_X = np.hstack([xgb_aligned, tft_aligned])

    # 简单加权融合 (无额外训练)
    weight_xgb = 0.55
    weight_tft = 0.45
    fused_proba = (
        weight_xgb * xgb_aligned + weight_tft * tft_aligned
    )
    fused_pred = np.argmax(fused_proba, axis=1)
    fused_acc = accuracy_score(y_aligned, fused_pred)

    print(f"  简单加权融合准确率: {fused_acc*100:.2f}%")
    print(f"    权重: XGBoost={weight_xgb}, TFT={weight_tft}")

    # 训练 Meta XGBoost
    meta_model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.05,
        objective="multi:softprob",
        num_class=3,
        random_state=42,
    )
    meta_model.fit(meta_X, y_aligned)
    meta_pred = meta_model.predict(meta_X)
    meta_acc = accuracy_score(y_aligned, meta_pred)

    print(f"  Meta XGBoost 融合准确率: {meta_acc*100:.2f}%")

    # 选最好的
    best_acc = max(fused_acc, meta_acc)
    best_method = (
        "weighted_fusion" if fused_acc >= meta_acc else "meta_xgboost"
    )
    print(f"\n  ✅ 最佳融合: {best_method} → {best_acc*100:.2f}%")
    print(f"{classification_report(y_aligned, fused_pred if best_method=='weighted_fusion' else meta_pred, target_names=['跌','平','涨'])}")

    if save:
        path = MODEL_DIR / f"stacking_{symbol.replace('/', '_')}.pkl"
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "weights": (weight_xgb, weight_tft),
                    "meta_model": meta_model,
                    "best_method": best_method,
                    "best_acc": best_acc,
                },
                f,
            )
        print(f"  💾 保存 → {path}")

    return best_acc


def ensemble_predict(xgb_model, tft_model, df_features, feature_cols, seq_len=60):
    """
    实时预测：融合 XGBoost 和 TFT 的概率。
    """
    from sklearn.preprocessing import StandardScaler

    # XGBoost 预测
    X = np.nan_to_num(df_features[feature_cols].values[-1:], nan=0)
    xgb_prob = xgb_model.predict_proba(X)

    # TFT 预测
    X_seq = df_features[feature_cols].values[-seq_len:]
    X_seq = np.nan_to_num(X_seq, nan=0)
    scaler = StandardScaler()
    X_seq = scaler.fit_transform(X_seq)
    import torch
    tft_model.eval()
    with torch.no_grad():
        t = torch.tensor(X_seq, dtype=torch.float32).unsqueeze(0)
        tft_prob = torch.softmax(tft_model(t), dim=1).numpy()

    # 融合
    fused = 0.55 * xgb_prob + 0.45 * tft_prob
    prediction = np.argmax(fused, axis=1)[0] - 1  # 换回 -1,0,1
    confidence = fused.max()

    labels = {1: "📈 涨", 0: "➡️ 平", -1: "📉 跌"}
    return labels.get(prediction, "unknown"), confidence
