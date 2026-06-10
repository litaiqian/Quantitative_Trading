"""
回测引擎 — 用训练好的模型在历史数据上模拟交易，评估策略效果
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional


class BacktestEngine:
    def __init__(
        self,
        initial_balance: float = 10000,
        commission: float = 0.001,  # OKX 现货 0.1%
        slippage: float = 0.0005,
    ):
        self.initial_balance = initial_balance
        self.commission = commission
        self.slippage = slippage

    def run(
        self,
        df: pd.DataFrame,
        predictions: np.ndarray,  # -1=跌, 0=平, 1=涨
        confidences: Optional[np.ndarray] = None,
        min_confidence: float = 0.5,
        stop_loss_atr: float = 2.0,
        take_profit_atr: float = 4.0,
    ) -> dict:
        """
        执行回测，返回统计数据。

        策略逻辑:
        - 预测=涨 & 置信度>阈值 → 买入
        - 预测=跌 → 卖出
        - ATR 动态止盈止损
        """
        balance = self.initial_balance
        position = 0
        entry_price = 0
        trades = []
        equity_curve = []

        prices = df["close"].values
        atr = df.get("atr", pd.Series(prices * 0.01)).values

        for i in range(len(predictions)):
            price = prices[i]
            cur_atr = atr[i] if not pd.isna(atr[i]) else price * 0.01
            equity = balance + (position * price if position > 0 else 0)
            equity_curve.append(equity)

            pred = predictions[i]
            conf = confidences[i] if confidences is not None else 1.0

            # 止盈止损
            if position > 0:
                pnl_pct = (price - entry_price) / entry_price
                if pnl_pct < -cur_atr * stop_loss_atr / price:
                    # 止损
                    exit_price = price * (1 - self.slippage)
                    revenue = position * exit_price * (1 - self.commission)
                    balance += revenue
                    trades.append(
                        {
                            "type": "STOP_LOSS",
                            "entry": entry_price,
                            "exit": exit_price,
                            "pnl": revenue - position * entry_price,
                            "pnl_pct": pnl_pct,
                            "index": i,
                        }
                    )
                    position = 0
                    entry_price = 0
                elif pnl_pct > cur_atr * take_profit_atr / price:
                    # 止盈
                    exit_price = price * (1 - self.slippage)
                    revenue = position * exit_price * (1 - self.commission)
                    balance += revenue
                    trades.append(
                        {
                            "type": "TAKE_PROFIT",
                            "entry": entry_price,
                            "exit": exit_price,
                            "pnl": revenue - position * entry_price,
                            "pnl_pct": pnl_pct,
                            "index": i,
                        }
                    )
                    position = 0
                    entry_price = 0

            # 交易信号
            if conf >= min_confidence:
                if pred == 1 and position == 0:
                    # 买入
                    size = balance * 0.95 / (price * (1 + self.slippage))
                    cost = size * price * (1 + self.slippage) * (1 + self.commission)
                    if cost <= balance:
                        position = size
                        entry_price = price * (1 + self.slippage)
                        balance -= cost
                        trades.append(
                            {
                                "type": "BUY",
                                "entry": entry_price,
                                "exit": None,
                                "pnl": None,
                                "pnl_pct": None,
                                "index": i,
                            }
                        )

                elif pred == -1 and position > 0:
                    # 卖出
                    exit_price = price * (1 - self.slippage)
                    revenue = position * exit_price * (1 - self.commission)
                    balance += revenue
                    pnl = revenue - position * entry_price
                    pnl_pct = (exit_price - entry_price) / entry_price
                    trades.append(
                        {
                            "type": "SELL",
                            "entry": entry_price,
                            "exit": exit_price,
                            "pnl": pnl,
                            "pnl_pct": pnl_pct,
                            "index": i,
                        }
                    )
                    position = 0
                    entry_price = 0

        # 收盘平仓
        if position > 0:
            last_price = prices[-1]
            revenue = position * last_price * (1 - self.commission)
            balance += revenue
            trades.append(
                {
                    "type": "CLOSE",
                    "entry": entry_price,
                    "exit": last_price,
                    "pnl": revenue - position * entry_price,
                    "pnl_pct": (last_price - entry_price) / entry_price,
                    "index": len(predictions) - 1,
                }
            )

        return self._calculate_stats(equity_curve, trades)

    def _calculate_stats(self, equity_curve: list, trades: list) -> dict:
        """计算回测统计"""
        equity = pd.Series(equity_curve)
        returns = equity.pct_change().dropna()

        total_return = (equity.iloc[-1] - self.initial_balance) / self.initial_balance

        sharpe = (
            returns.mean() / (returns.std() + 1e-9) * np.sqrt(252 * 24)
            if len(returns) > 1
            else 0
        )

        # 最大回撤
        peak = equity.expanding().max()
        drawdown = (equity - peak) / peak
        max_drawdown = drawdown.min()

        # 胜率
        closed_trades = [t for t in trades if t["pnl"] is not None]
        wins = [t for t in closed_trades if t["pnl"] > 0]
        win_rate = len(wins) / len(closed_trades) if closed_trades else 0

        # 盈亏比
        avg_win = np.mean([t["pnl"] for t in wins]) if wins else 0
        losses = [t for t in closed_trades if t["pnl"] <= 0]
        avg_loss = abs(np.mean([t["pnl"] for t in losses])) if losses else 0
        profit_factor = (avg_win / (avg_loss + 1e-9) if avg_loss > 0 else float("inf"))

        return {
            "total_return": total_return,
            "sharpe_ratio": float(sharpe),
            "max_drawdown": float(max_drawdown),
            "win_rate": float(win_rate),
            "total_trades": len(closed_trades),
            "profit_factor": float(profit_factor),
            "final_balance": float(equity.iloc[-1]),
            "equity_curve": equity_curve,
            "trades": trades,
        }


def print_report(stats: dict, symbol: str = ""):
    """打印回测报告"""
    print(f"\n{'='*50}")
    print(f"  📊 回测报告{f' — {symbol}' if symbol else ''}")
    print(f"{'='*50}")
    print(f"  初始资金:     ${stats.get('initial_balance', 10000):,.2f}")
    print(f"  最终资金:     ${stats['final_balance']:,.2f}")
    print(f"  总收益率:     {stats['total_return']*100:+.2f}%")
    print(f"  夏普比率:     {stats['sharpe_ratio']:.3f}")
    print(f"  最大回撤:     {stats['max_drawdown']*100:.2f}%")
    print(f"  胜率:         {stats['win_rate']*100:.1f}%")
    print(f"  交易次数:     {stats['total_trades']}")
    print(f"  盈亏比:       {stats['profit_factor']:.2f}")

    # 标杆对比
    print(f"\n  🏷  vs 买入持有 BTC:")
    buy_hold_return = (
        stats.get("buy_hold_return", stats["total_return"])
        if "buy_hold_return" in stats
        else 0
    )
    alpha = stats["total_return"] - buy_hold_return
    print(f"     Alpha:  {alpha*100:+.2f}%")
