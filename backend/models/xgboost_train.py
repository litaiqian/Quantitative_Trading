"""
XGBoost 主预测器 — 涨/跌/平 三分类
"""

import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
)
import xgboost as xgb

MODEL_DIR = Path(__file__).parent / "saved"
MODEL_DIR.mkdir(exist_ok=True)


def prepare_data(df: pd.DataFrame, feature_cols: list):
    """准备训练/测试数据"""
    X = df[feature_cols].values
    y = df["target_class"].values + 1  # -1,0,1 → 0,1,2

    mask = ~np.isnan(X).any(axis=1) & ~np.isnan(y)
    X, y = X[mask], y[mask]

    return train_test_split(X, y, test_size=0.2, shuffle=False)


def train(
    df: pd.DataFrame,
    feature_cols: list,
    symbol: str = "BTC/USDT",
    save: bool = True,
) -> tuple:
    """训练 XGBoost 分类器"""
    print(f"\n{'='*50}")
    print(f"  🎯 XGBoost 训练 — {symbol}")
    print(f"{'='*50}")

    X_train, X_test, y_train, y_test = prepare_data(df, feature_cols)

    # 处理类别不平衡
    counts = np.bincount(y_train.astype(int), minlength=3)
    scale_pos_weights = [sum(counts) / (3 * c) if c > 0 else 1.0 for c in counts]

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="multi:softprob",
        num_class=3,
        eval_metric="mlogloss",
        early_stopping_rounds=20,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_test, y_test)],
        verbose=50,
    )

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\n  ✅ 准确率: {acc*100:.2f}%")
    print(f"\n{classification_report(y_test, y_pred, target_names=['跌','平','涨'])}")

    # 特征重要性
    importance = pd.DataFrame(
        {"feature": feature_cols, "importance": model.feature_importances_}
    ).sort_values("importance", ascending=False)
    print(f"\n  📊 Top 10 特征:")
    for _, row in importance.head(10).iterrows():
        print(f"    {row['feature']:<30} {row['importance']:.4f}")

    # 概率校准 (用于 stacking)
    proba = model.predict_proba(X_test)

    if save:
        path = MODEL_DIR / f"xgboost_{symbol.replace('/', '_')}.pkl"
        with open(path, "wb") as f:
            pickle.dump(model, f)
        print(f"\n  💾 保存模型 → {path}")

    return model, y_test, proba


def predict(model, df: pd.DataFrame, feature_cols: list) -> np.ndarray:
    """用训练好的模型预测"""
    X = df[feature_cols].values
    X = np.nan_to_num(X, nan=0)
    return model.predict_proba(X)
