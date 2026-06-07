"""
AI Strategy Engine - Multi-model prediction for crypto trading
"""
from __future__ import annotations
from typing import Dict, Tuple
import warnings
warnings.filterwarnings("ignore")
# Lazy imports for heavy ML packages
pd = None
np = None
RandomForestClassifier = None
StandardScaler = None

def _ensure_ml():
    global pd, np, RandomForestClassifier, StandardScaler
    if RandomForestClassifier is None:
        import importlib
        try:
            pd = importlib.import_module("pandas")
            np = importlib.import_module("numpy")
            sklearn_ensemble = importlib.import_module("sklearn.ensemble")
            RandomForestClassifier = sklearn_ensemble.RandomForestClassifier
            sklearn_preprocessing = importlib.import_module("sklearn.preprocessing")
            StandardScaler = sklearn_preprocessing.StandardScaler
        except ImportError:
            raise ImportError("请先安装 ML 依赖: pip install pandas numpy scikit-learn")

class AIStrategy:
    """AI 驱动的交易策略引擎"""

    def __init__(self):
        _ensure_ml()
        self.model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False

    def compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标特征"""
        df = df.copy()

        # 价格特征
        df["returns"] = df["close"].pct_change()
        df["log_returns"] = np.log(df["close"] / df["close"].shift(1))
        df["volatility"] = df["returns"].rolling(20).std()
        df["high_low_ratio"] = (df["high"] - df["low"]) / df["close"]
        df["volume_ratio"] = df["volume"] / df["volume"].rolling(20).mean()

        # 移动平均
        for window in [5, 10, 20, 50]:
            df[f"ma_{window}"] = df["close"].rolling(window).mean()
            df[f"price_to_ma_{window}"] = df["close"] / df[f"ma_{window}"]

        # RSI
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-10)
        df["rsi"] = 100 - (100 / (1 + rs))

        # MACD
        ema12 = df["close"].ewm(span=12).mean()
        ema26 = df["close"].ewm(span=26).mean()
        df["macd"] = ema12 - ema26
        df["macd_signal"] = df["macd"].ewm(span=9).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        # 布林带
        df["bb_mid"] = df["close"].rolling(20).mean()
        bb_std = df["close"].rolling(20).std()
        df["bb_upper"] = df["bb_mid"] + 2 * bb_std
        df["bb_lower"] = df["bb_mid"] - 2 * bb_std
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]
        df["bb_position"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"] + 1e-10)

        return df

    def prepare_labels(self, df: pd.DataFrame, forward_periods: int = 6) -> pd.Series:
        """生成标签：未来 N 根 K 线是否上涨超过 1%"""
        future_price = df["close"].shift(-forward_periods)
        future_return = (future_price - df["close"]) / df["close"]
        return (future_return > 0.01).astype(int)

    def train(self, df: pd.DataFrame) -> Dict:
        """训练 AI 模型"""
        df = self.compute_features(df)
        labels = self.prepare_labels(df)

        # 选择特征列
        feature_cols = [c for c in df.columns if c not in ["open", "high", "low", "close", "volume", "timestamp"]]
        X = df[feature_cols].dropna()
        y = labels.loc[X.index]

        if len(X) < 100:
            return {"status": "failed", "reason": "数据不足，至少需要100条K线"}

        # 训练/验证拆分 (80/20)
        split = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]

        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        self.model.fit(X_train_scaled, y_train)
        train_acc = self.model.score(X_train_scaled, y_train)
        test_acc = self.model.score(X_test_scaled, y_test)
        self.is_trained = True

        # 特征重要性
        importance = dict(zip(feature_cols, self.model.feature_importances_))
        top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "status": "trained",
            "train_accuracy": round(train_acc, 4),
            "test_accuracy": round(test_acc, 4),
            "samples": len(X),
            "top_features": [{"name": f[0], "importance": round(f[1], 4)} for f in top_features],
        }

    def predict(self, df: pd.DataFrame) -> Dict:
        """预测信号"""
        if not self.is_trained:
            return {"signal": "hold", "confidence": 0, "reason": "模型未训练"}

        df = self.compute_features(df)
        feature_cols = [c for c in df.columns if c not in ["open", "high", "low", "close", "volume", "timestamp"]]
        latest = df[feature_cols].iloc[-1:].dropna()

        if latest.empty:
            return {"signal": "hold", "confidence": 0, "reason": "特征缺失"}

        X = self.scaler.transform(latest)
        proba = self.model.predict_proba(X)[0]
        pred = self.model.predict(X)[0]
        confidence = proba[1] if pred == 1 else proba[0]

        # 生成交易信号
        if pred == 1 and confidence > 0.6:
            signal = "buy" if confidence > 0.75 else "buy_weak"
        elif pred == 0 and confidence > 0.55:
            signal = "sell"
        else:
            signal = "hold"

        return {
            "signal": signal,
            "confidence": round(float(confidence), 4),
            "buy_probability": round(float(proba[1]), 4),
            "sell_probability": round(float(proba[0]), 4),
            "current_price": round(float(df["close"].iloc[-1]), 2),
            "rsi": round(float(df["rsi"].iloc[-1]), 2) if "rsi" in df.columns else None,
        }
