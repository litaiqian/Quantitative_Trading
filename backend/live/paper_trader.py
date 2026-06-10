"""
模拟盘交易执行 — 对接 OKX Demo 交易
用训练好的模型产生信号，模拟盘自动下单
"""

import time
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

MODEL_DIR = Path(__file__).parent.parent / "models" / "saved"


class PaperTrader:
    """模拟盘自动交易"""

    def __init__(self, symbol: str = "BTC/USDT"):
        self.symbol = symbol
        self.safe_name = symbol.replace("/", "_")

        # 加载模型
        self.xgb_model = None
        self.tft_model = None
        self.ppo_policy = None
        self._load_models()

    def _load_models(self):
        """加载训练好的模型"""
        xgb_path = MODEL_DIR / f"xgboost_{self.safe_name}.pkl"
        tft_path = MODEL_DIR / f"tft_{self.safe_name}.pkl"
        ppo_path = MODEL_DIR / f"ppo_{self.safe_name}.pkl"

        if xgb_path.exists():
            with open(xgb_path, "rb") as f:
                self.xgb_model = pickle.load(f)
            print(f"  ✅ 加载 XGBoost: {xgb_path}")

        if tft_path.exists():
            with open(tft_path, "rb") as f:
                tft_data = pickle.load(f)
                self.tft_model = tft_data["model"]
                self.tft_scaler = tft_data["scaler"]
            print(f"  ✅ 加载 TFT: {tft_path}")

        if ppo_path.exists():
            with open(ppo_path, "rb") as f:
                ppo_data = pickle.load(f)
                self.ppo_policy = ppo_data["policy"]
            print(f"  ✅ 加载 PPO: {ppo_path}")

    def run(self, interval_seconds: int = 60, rounds: int = 1000):
        """
        模拟盘循环:
        1. 获取最新 K 线
        2. 计算特征
        3. XGBoost+TFT 预测方向
        4. PPO 决定仓位
        5. 通过 OKX 模拟盘 API 下单
        """
        import ccxt

        exchange = ccxt.okx(
            {
                "apiKey": "YOUR_API_KEY",
                "secret": "YOUR_SECRET",
                "password": "YOUR_PASSPHRASE",
            }
        )
        # 模拟盘
        exchange.headers["x-simulated-trading"] = "1"

        print(f"\n{'='*50}")
        print(f"  🎮 模拟盘启动 — {self.symbol}")
        print(f"    间隔: {interval_seconds}s")
        print(f"    模型: XGBoost + TFT + PPO")
        print(f"{'='*50}")

        for round_num in range(rounds):
            try:
                # 获取最新K线
                ohlcv = exchange.fetch_ohlcv(
                    self.symbol, "15m", limit=200
                )
                df = pd.DataFrame(
                    ohlcv,
                    columns=["timestamp", "open", "high", "low", "close", "volume"],
                )

                # 计算特征
                from features import technical, kalman_filter, garch

                df = technical.add_all_features(df)
                df = kalman_filter.add_kalman_features(df)
                df = garch.add_garch_features(df)

                latest = df.iloc[-1:]

                # 预测
                if self.xgb_model is not None:
                    feature_cols = technical.get_feature_columns(df)
                    X = np.nan_to_num(
                        latest[feature_cols].values, nan=0
                    )
                    xgb_proba = self.xgb_model.predict_proba(X)[0]

                    pred_idx = np.argmax(xgb_proba)
                    labels = {-1: "📉 跌", 0: "➡️ 平", 1: "📈 涨"}
                    pred_label = labels.get(pred_idx, "?")
                    confidence = xgb_proba.max()

                    print(
                        f"  [{datetime.now().strftime('%H:%M:%S')}] "
                        f"BTC={df['close'].iloc[-1]:.2f}  "
                        f"预测={pred_label}  "
                        f"置信度={confidence:.1%}"
                    )

                    # PPO 决策
                    if self.ppo_policy is not None:
                        from models.ppo_train import get_action

                        vol = latest.get("garch_vol", pd.Series([0.02])).iloc[0]
                        price = latest["close"].iloc[0]
                        state = np.array(
                            [
                                xgb_proba[2],
                                xgb_proba[1],
                                xgb_proba[0],
                                vol * 100 if not pd.isna(vol) else 2,
                                0,
                                0,
                            ],
                            dtype=np.float32,
                        )
                        _, action_name = get_action(self.ppo_policy, state)
                        print(f"    PPO: {action_name}")

                        if action_name == "BUY":
                            balance = exchange.fetch_balance()
                            usdt = balance["USDT"]["free"]
                            order = exchange.create_order(
                                self.symbol,
                                "market",
                                "buy",
                                usdt * 0.8 / price,
                            )
                            print(f"    ✅ 下单: BUY {order['amount']}")

                        elif action_name == "SELL":
                            order = exchange.create_order(
                                self.symbol, "market", "sell", None
                            )
                            print(f"    ✅ 下单: SELL")

            except Exception as e:
                print(f"  ⚠️ 错误: {e}")

            time.sleep(interval_seconds)


if __name__ == "__main__":
    trader = PaperTrader("BTC/USDT")
    trader.run(interval_seconds=60, rounds=100)
