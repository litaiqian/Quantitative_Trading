"""
PPO 仓位管理 — 强化学习决策：基于预测概率+波动率，决定买多少、止盈止损
"""

import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from collections import deque
import random
import torch
import torch.nn as nn
from torch.distributions import Categorical

MODEL_DIR = Path(__file__).parent / "saved"
MODEL_DIR.mkdir(exist_ok=True)


class TradingEnv:
    """简化交易环境，用于 PPO 训练"""

    def __init__(
        self,
        df: pd.DataFrame,
        prediction_proba: np.ndarray,
        initial_balance: float = 10000,
        commission: float = 0.001,
    ):
        self.df = df.reset_index(drop=True)
        self.pred_proba = prediction_proba
        self.initial_balance = initial_balance
        self.commission = commission

        self.balance = initial_balance
        self.position = 0  # 持仓量 (正=多, 负=空)
        self.entry_price = 0
        self.current_step = 0
        self.max_steps = len(df) - 1

        self.trade_history = []
        self.portfolio_values = []

    def reset(self):
        self.balance = self.initial_balance
        self.position = 0
        self.entry_price = 0
        self.current_step = 0
        self.trade_history = []
        self.portfolio_values = []
        return self._get_state()

    def _get_state(self):
        """状态: 预测概率(3) + 波动率 + 仓位率 + 盈亏比"""
        proba = self.pred_proba[self.current_step]  # 涨/平/跌 概率
        vol = self.df.iloc[self.current_step].get("garch_vol", 0.02)
        if pd.isna(vol):
            vol = 0.02

        price = self.df.iloc[self.current_step]["close"]
        portfolio_value = self.balance + (
            self.position * price if self.position > 0 else 0
        )
        position_ratio = self.position * price / (portfolio_value + 1)

        # 未实现盈亏
        if self.position > 0:
            pnl_pct = (price - self.entry_price) / self.entry_price
        else:
            pnl_pct = 0

        return np.array(
            [
                proba[2],  # 涨概率
                proba[1],  # 平概率
                proba[0],  # 跌概率
                vol * 100,
                position_ratio,
                pnl_pct * 10,
            ],
            dtype=np.float32,
        )

    def step(self, action: int):
        """
        action: 0=持有, 1=买入(加仓), 2=卖出(减仓/清仓)
        """
        price = self.df.iloc[self.current_step]["close"]
        atr = self.df.iloc[self.current_step].get("atr", price * 0.01)
        if pd.isna(atr):
            atr = price * 0.01

        prev_value = self.balance + (
            self.position * price if self.position > 0 else 0
        )

        # 执行动作
        if action == 1 and self.position == 0:  # 买入
            size = self.balance * 0.8 / (price + 1e-9)  # 用 80% 资金
            cost = size * price * (1 + self.commission)
            if cost <= self.balance:
                self.position = size
                self.entry_price = price
                self.balance -= cost
                self.trade_history.append(("BUY", price, size))

        elif action == 2 and self.position > 0:  # 卖出
            revenue = self.position * price * (1 - self.commission)
            self.balance += revenue
            pnl = revenue - self.position * self.entry_price
            self.trade_history.append(
                ("SELL", price, self.position, pnl)
            )
            self.position = 0
            self.entry_price = 0

        # 止损 (ATR × 2)
        if self.position > 0:
            loss_pct = (price - self.entry_price) / self.entry_price
            if loss_pct < -atr * 2 / price:
                revenue = self.position * price * (1 - self.commission)
                self.balance += revenue
                pnl = revenue - self.position * self.entry_price
                self.trade_history.append(
                    ("STOP_LOSS", price, self.position, pnl)
                )
                self.position = 0
                self.entry_price = 0

        self.current_step += 1
        done = self.current_step >= self.max_steps

        # 奖励 = 资产增长率
        new_value = self.balance + (
            self.position * self.df.iloc[self.current_step]["close"]
            if self.position > 0 and not done
            else 0
        )
        reward = (new_value - prev_value) / (prev_value + 1)

        return self._get_state() if not done else np.zeros(6), reward, done

    def get_stats(self):
        """计算回测统计"""
        if len(self.trade_history) < 2:
            return {"total_return": 0, "sharpe": 0, "max_drawdown": 0, "trades": 0}

        final_value = self.balance + (
            self.position * self.df.iloc[self.max_steps - 1]["close"]
            if self.position > 0
            else 0
        )
        total_return = (final_value - self.initial_balance) / self.initial_balance

        # 简化的夏普比率
        sells = [t for t in self.trade_history if t[0] in ("SELL", "STOP_LOSS")]
        if sells:
            returns = [t[3] / self.initial_balance for t in sells if len(t) > 3]
            sharpe = np.mean(returns) / (np.std(returns) + 1e-9) * np.sqrt(252) if returns else 0
        else:
            sharpe = 0

        return {
            "total_return": total_return,
            "sharpe": float(sharpe),
            "max_drawdown": 0,
            "trades": len(self.trade_history) // 2,
        }


class PPOPolicy(nn.Module):
    def __init__(self, state_dim=6, action_dim=3, hidden=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, action_dim),
        )

    def forward(self, x):
        return self.net(x)


def train_ppo(
    df: pd.DataFrame,
    proba: np.ndarray,
    symbol: str = "BTC/USDT",
    episodes: int = 200,
    save: bool = True,
):
    """PPO 训练 (简化版)"""
    print(f"\n{'='*50}")
    print(f"  🤖 PPO 仓位管理训练 — {symbol}")
    print(f"{'='*50}")

    env = TradingEnv(df, proba)
    device = torch.device("cpu")
    policy = PPOPolicy().to(device)
    optimizer = torch.optim.Adam(policy.parameters(), lr=3e-4)

    best_reward = -float("inf")

    for episode in range(episodes):
        state = env.reset()
        log_probs = []
        rewards = []
        values = []

        while True:
            state_t = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
            logits = policy(state_t)
            dist = Categorical(logits=logits)
            action = dist.sample()

            log_probs.append(dist.log_prob(action))
            next_state, reward, done = env.step(action.item())
            rewards.append(reward)

            if done:
                break
            state = next_state

        # 简化的 PPO 更新
        returns = []
        R = 0
        for r in reversed(rewards):
            R = r + 0.99 * R
            returns.insert(0, R)
        returns = torch.tensor(returns, dtype=torch.float32)
        returns = (returns - returns.mean()) / (returns.std() + 1e-8)

        log_probs = torch.stack(log_probs)
        advantages = returns

        loss = -(log_probs * advantages).mean()
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_reward = sum(rewards)
        if total_reward > best_reward:
            best_reward = total_reward

        if (episode + 1) % 50 == 0:
            stats = env.get_stats()
            print(
                f"  Episode {episode+1:3d}  "
                f"reward={total_reward:.3f}  "
                f"return={stats['total_return']*100:+.1f}%  "
                f"sharpe={stats['sharpe']:.2f}"
            )

    stats = env.get_stats()
    print(f"\n  ✅ 训练完成 — 收益: {stats['total_return']*100:+.1f}%, "
          f"夏普: {stats['sharpe']:.2f}, 交易: {stats['trades']}次")

    if save:
        path = MODEL_DIR / f"ppo_{symbol.replace('/', '_')}.pkl"
        with open(path, "wb") as f:
            pickle.dump(
                {"policy": policy, "stats": stats}, f
            )
        print(f"  💾 保存 → {path}")

    return policy, stats


def get_action(
    policy, state: np.ndarray
) -> tuple:
    """获取 PPO 动作 (0=持有, 1=买入, 2=卖出)"""
    device = next(policy.parameters()).device
    with torch.no_grad():
        logits = policy(
            torch.tensor(state, dtype=torch.float32).unsqueeze(0).to(device)
        )
        action = logits.argmax(dim=1).item()
    actions = {0: "HOLD", 1: "BUY", 2: "SELL"}
    return action, actions[action]
