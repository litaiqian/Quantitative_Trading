"""
GARCH 波动率预测 — 用 GARCH(1,1) 建模收益率波动
"""

import numpy as np
import pandas as pd
from arch import arch_model


def fit_garch(returns: pd.Series, forecast_horizon: int = 1) -> pd.Series:
    """
    对收益率序列滚动拟合 GARCH(1,1)，预测未来波动率。
    - 滚动窗口：500 根 K 线
    - 返回：每根 K 线的下一期波动率预测
    """
    n = len(returns)
    vol_forecast = pd.Series(np.nan, index=returns.index)
    window = min(500, n - 10)

    for i in range(window, n):
        if i % 500 == 0:
            print(f"    GARCH 滚动拟合: {i}/{n}")

        try:
            train = returns.iloc[i - window : i].dropna() * 100  # 缩放便于拟合
            if len(train) < 100 or train.std() < 1e-6:
                vol_forecast.iloc[i] = returns.iloc[max(0, i - 20) : i].std()
                continue

            model = arch_model(train, vol="Garch", p=1, q=1, dist="normal")
            result = model.fit(disp="off")
            vol_forecast.iloc[i] = result.forecast(horizon=forecast_horizon).variance.iloc[
                -1, 0
            ] / 10000  # 缩放回去
        except Exception:
            vol_forecast.iloc[i] = returns.iloc[max(0, i - 20) : i].std()

    # 填前 window 段用滚动标准差
    vol_forecast.iloc[:window] = (
        returns.iloc[:window].rolling(20).std().iloc[-1]
        if len(returns[:window]) > 0
        else returns.std()
    )

    return vol_forecast


def add_garch_features(df: pd.DataFrame) -> pd.DataFrame:
    """将 GARCH 波动率特征加入 DataFrame"""
    df = df.copy()
    returns = df["returns"].dropna()
    print(f"  🧮 正在拟合 GARCH ({len(returns)} 个样本)...")

    df.loc[returns.index, "garch_vol"] = fit_garch(returns)
    df["garch_vol"].fillna(method="ffill", inplace=True)

    # 波动率变化率
    df["garch_vol_change"] = df["garch_vol"].pct_change()

    # 波动率状态
    vol_median = df["garch_vol"].rolling(100).median()
    df["garch_high_vol"] = (df["garch_vol"] > 1.5 * vol_median).astype(int)

    # 波动率锥位置 (当前波动率在历史中的百分位)
    df["garch_percentile"] = df["garch_vol"].rolling(200).rank(pct=True)

    return df
