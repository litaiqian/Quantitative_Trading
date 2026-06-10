"""
OKX 数据采集器 — 拉取历史 K 线，支持多币种、多粒度、多时间范围。
公开接口，不需要 API Key。
频率限制：20次/2秒，自动限速。
"""

import ccxt
import pandas as pd
import time
from pathlib import Path
from datetime import datetime, timedelta

DATA_DIR = Path(__file__).parent  # backend/data/

# 目标交易对与粒度配置
SYMBOLS = ["BTC/USDT", "ETH/USDT"]
TIMEFRAMES = {
    "1h": "1h",
    "15m": "15m",
    "5m": "5m",
}


def fetch_ohlcv(symbol: str, timeframe: str, since: int, limit: int = 300):
    """从 OKX 拉取 OHLCV 数据，带重试和限速"""
    exchange = ccxt.okx({"enableRateLimit": True})
    all_candles = []
    current_since = since

    while True:
        try:
            candles = exchange.fetch_ohlcv(
                symbol, timeframe, since=current_since, limit=limit
            )
            if not candles:
                break
            all_candles.extend(candles)
            current_since = candles[-1][0] + 1
            time.sleep(0.2)  # 20次/2秒的余量
        except Exception as e:
            print(f"  ⚠️ 拉取出错, 等待重试: {e}")
            time.sleep(3)

        if current_since > int(datetime.now().timestamp() * 1000):
            break

    return all_candles


def candles_to_df(candles: list) -> pd.DataFrame:
    """将 ccxt 格式转为 DataFrame"""
    df = pd.DataFrame(
        candles, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df


def collect_all(years: int = 3):
    """拉取所有配置的币种和粒度，保存为 CSV"""
    since = int((datetime.now() - timedelta(days=years * 365)).timestamp() * 1000)

    for symbol in SYMBOLS:
        safe_name = symbol.replace("/", "_")
        for tf_name, tf_ccxt in TIMEFRAMES.items():
            print(f"\n📡 拉取 {symbol} {tf_name} K线...")
            candles = fetch_ohlcv(symbol, tf_ccxt, since)
            df = candles_to_df(candles)
            csv_path = DATA_DIR / f"{safe_name}_{tf_name}.csv"
            df.to_csv(csv_path)
            print(f"  ✅ 保存 {len(df)} 条 → {csv_path}")


def load_data(symbol: str, timeframe: str) -> pd.DataFrame:
    """加载本地 CSV 数据"""
    safe_name = symbol.replace("/", "_")
    csv_path = DATA_DIR / f"{safe_name}_{tf_name}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"先运行 okx_collector.py: {csv_path}")
    df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    return df


if __name__ == "__main__":
    print("=" * 60)
    print("  OKX 数据采集器 — BTC/ETH 3年K线")
    print("=" * 60)
    t0 = time.time()
    collect_all(years=3)
    print(f"\n⏱ 总耗时: {time.time()-t0:.0f} 秒")
