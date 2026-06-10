"""
卡尔曼滤波器 — 对价格序列去噪，提取平滑趋势线
"""

import numpy as np
import pandas as pd


def kalman_smooth(series: pd.Series, process_noise: float = 0.001) -> pd.Series:
    """
    标准卡尔曼滤波，适用于价格序列。
    - process_noise: 过程噪声，越小越平滑但越滞后。
    """
    n = len(series)
    x_est = series.iloc[0]  # 初始状态
    p_est = 1.0  # 初始协方差

    measurement_noise = series.diff().std() ** 2  # 观测噪声从数据估算

    smoothed = np.zeros(n)
    smoothed[0] = x_est

    for i in range(1, n):
        # 预测
        x_pred = x_est
        p_pred = p_est + process_noise

        # 更新
        k = p_pred / (p_pred + measurement_noise)  # 卡尔曼增益
        x_est = x_pred + k * (series.iloc[i] - x_pred)
        p_est = (1 - k) * p_pred

        smoothed[i] = x_est

    return pd.Series(smoothed, index=series.index)


def add_kalman_features(df: pd.DataFrame) -> pd.DataFrame:
    """将卡尔曼滤波特征加入 DataFrame"""
    df = df.copy()

    close = df["close"]
    df["kalman_close"] = kalman_smooth(close, process_noise=0.0005)

    # 卡尔曼趋势线斜率 (滚动回归)
    df["kalman_trend"] = df["kalman_close"].diff(5) / df["kalman_close"].shift(5)

    # 价格与卡尔曼线的偏离
    df["kalman_deviation"] = (close - df["kalman_close"]) / df["kalman_close"] * 100

    # 卡尔曼趋势信号
    df["kalman_signal"] = (
        (df["kalman_close"] > df["kalman_close"].shift(20)).astype(int)
        + (df["kalman_close"] > df["kalman_close"].shift(50)).astype(int)
    )  # 0=强下跌, 1=弱, 2=强上涨

    return df
