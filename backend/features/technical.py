"""
特征工厂 — 技术指标特征生成
MA, MACD, RSI, ATR, 布林带, 动量因子等 50+ 特征
"""

import numpy as np
import pandas as pd
from typing import Tuple


def add_all_features(df: pd.DataFrame) -> pd.DataFrame:
    """给 DataFrame 添加全部技术指标特征"""
    df = df.copy()

    # === 收益率 ===
    df["returns"] = df["close"].pct_change()
    df["log_returns"] = np.log(df["close"] / df["close"].shift(1))

    # === 移动平均 ===
    for window in [5, 10, 20, 50, 100, 200]:
        df[f"sma_{window}"] = df["close"].rolling(window).mean()
        df[f"ema_{window}"] = df["close"].ewm(span=window, adjust=False).mean()
        df[f"volume_sma_{window}"] = df["volume"].rolling(window).mean()
        # 价格偏离均线百分比
        if window >= 20:
            df[f"price_vs_sma{window}"] = (
                (df["close"] - df[f"sma_{window}"]) / df[f"sma_{window}"] * 100
            )

    # === MACD ===
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    df["macd_cross"] = (df["macd"] > df["macd_signal"]).astype(int)

    # === RSI ===
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    df["rsi"] = 100 - (100 / (1 + rs))
    df["rsi_overbought"] = (df["rsi"] > 70).astype(int)
    df["rsi_oversold"] = (df["rsi"] < 30).astype(int)

    # === 布林带 ===
    sma20 = df["close"].rolling(20).mean()
    std20 = df["close"].rolling(20).std()
    df["bb_upper"] = sma20 + 2 * std20
    df["bb_lower"] = sma20 - 2 * std20
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / sma20
    df["bb_position"] = (df["close"] - df["bb_lower"]) / (
        df["bb_upper"] - df["bb_lower"] + 1e-9
    )
    df["bb_squeeze"] = (df["bb_width"] < df["bb_width"].rolling(20).mean()).astype(int)

    # === ATR (平均真实波幅) ===
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.ewm(span=14, adjust=False).mean()
    df["atr_pct"] = df["atr"] / df["close"] * 100

    # === 动量因子 ===
    for window in [3, 5, 10, 20, 50]:
        df[f"momentum_{window}"] = df["close"].pct_change(window)
        df[f"roc_{window}"] = (df["close"] - df["close"].shift(window)) / df[
            "close"
        ].shift(window) * 100

    # === 波动率 ===
    for window in [5, 10, 20, 50]:
        df[f"volatility_{window}"] = df["returns"].rolling(window).std()

    # === 成交量因子 ===
    df["volume_ratio"] = df["volume"] / df["volume"].rolling(20).mean()
    df["volume_trend"] = (df["volume"] > df["volume"].shift(10)).astype(int)

    # === 高低价特征 ===
    df["high_low_pct"] = (df["high"] - df["low"]) / df["close"] * 100
    df["close_position"] = (df["close"] - df["low"]) / (df["high"] - df["low"] + 1e-9)
    df["gap"] = (df["open"] - df["close"].shift(1)) / df["close"].shift(1) * 100

    # === 趋势强度 (ADX 简化) ===
    plus_dm = df["high"].diff().clip(lower=0)
    minus_dm = -df["low"].diff().clip(upper=0)
    df["di_plus"] = 100 * plus_dm.ewm(span=14, adjust=False).mean() / (df["atr"] + 1e-9)
    df["di_minus"] = (
        100 * minus_dm.ewm(span=14, adjust=False).mean() / (df["atr"] + 1e-9)
    )
    dx = (df["di_plus"] - df["di_minus"]).abs() / (
        df["di_plus"] + df["di_minus"] + 1e-9
    ) * 100
    df["adx"] = dx.ewm(span=14, adjust=False).mean()
    df["trend_strength"] = (df["adx"] > 25).astype(int)

    # === 目标变量 (预测下根K线方向) ===
    df["target_direction"] = (df["close"].shift(-1) > df["close"]).astype(int)
    df["target_return"] = df["close"].pct_change().shift(-1)
    df["target_class"] = np.where(
        df["target_return"] > 0.005,
        1,  # 涨超0.5%
        np.where(
            df["target_return"] < -0.005,
            -1,  # 跌超0.5%
            0,  # 横盘
        ),
    )

    return df.dropna()


def get_feature_columns(df: pd.DataFrame) -> list:
    """返回所有特征列名 (排除目标变量和非特征列)"""
    exclude = {
        "target_direction",
        "target_return",
        "target_class",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "returns",
        "log_returns",
    }
    return [c for c in df.columns if c not in exclude]
