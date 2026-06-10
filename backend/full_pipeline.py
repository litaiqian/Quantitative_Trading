"""
全流程自动化 — 拉数据 → 特征工程 → 训练 → 回测 → 评估
一键运行: python full_pipeline.py
"""

import sys
import time
from pathlib import Path

# 确保可以导入 backend 下的模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.okx_collector import collect_all, load_data
from features.technical import add_all_features, get_feature_columns
from features.kalman_filter import add_kalman_features
from features.garch import add_garch_features
from features.sentiment import SentimentAnalyzer, add_sentiment_features
from models.xgboost_train import train as train_xgboost
from models.tft_train import train as train_tft
from models.stacking import stack_predictions
from models.ppo_train import train_ppo
from backtest.engine import BacktestEngine, print_report


def pipeline(symbol: str = "BTC/USDT", use_garch: bool = True):
    """完整训练流程"""
    safe = symbol.replace("/", "_")
    t0 = time.time()

    # ── 第1步: 拉数据 ──
    print("\n" + "=" * 60)
    print("  📡 第1步: 拉取 OKX 数据")
    print("=" * 60)
    collect_all(years=3)

    # ── 第2步: 加载 + 特征工程 ──
    print("\n" + "=" * 60)
    print("  🏗 第2步: 特征工程")
    print("=" * 60)
    df = load_data(symbol, "1h")
    print(f"  原始数据: {len(df)} 行")

    df = add_all_features(df)
    df = add_kalman_features(df)

    if use_garch:
        df = add_garch_features(df)

    # 新闻情绪 (模拟)
    print("  📰 加载新闻情绪...")
    analyzer = SentimentAnalyzer()
    sentiment = analyzer.get_market_sentiment()
    print(f"    当前情绪: {sentiment['sentiment_label']} ({sentiment['sentiment_score']:+.2f})")
    df = add_sentiment_features(df, sentiment)

    df = df.dropna()
    feature_cols = get_feature_columns(df)
    print(f"  特征工程后: {len(df)} 行 × {len(feature_cols)} 特征")

    # ── 第3步: XGBoost ──
    print("\n" + "=" * 60)
    print("  🎯 第3步: XGBoost 训练")
    print("=" * 60)
    xgb_model, y_test, xgb_proba = train_xgboost(df, feature_cols, symbol)

    # ── 第4步: TFT (可选, 需要 GPU) ──
    print("\n" + "=" * 60)
    print("  🧠 第4步: TFT 训练")
    print("=" * 60)
    try:
        tft_model, tft_y_test, tft_proba = train_tft(df, feature_cols, symbol)
        tft_available = True
    except Exception as e:
        print(f"  ⚠️ TFT 训练跳过 ({e})")
        tft_available = False
        tft_proba = xgb_proba  # 回退

    # ── 第5步: Stacking ──
    if tft_available:
        print("\n" + "=" * 60)
        print("  🔗 第5步: Stacking 融合")
        print("=" * 60)
        best_acc = stack_predictions(xgb_proba, tft_proba, y_test, symbol)

    # ── 第6步: PPO ──
    print("\n" + "=" * 60)
    print("  🤖 第6步: PPO 仓位管理")
    print("=" * 60)
    ppo_policy, ppo_stats = train_ppo(df, xgb_proba, symbol)

    # ── 第7步: 回测 ──
    print("\n" + "=" * 60)
    print("  📊 第7步: 回测验证")
    print("=" * 60)

    # 生成预测
    import numpy as np
    from models.stacking import ensemble_predict

    predictions = []
    confidences = []
    for i in range(len(df)):
        if i < 60:  # TFT 需要 seq_len
            pred = np.argmax(xgb_proba[min(i, len(xgb_proba) - 1)]) - 1
            conf = xgb_proba[min(i, len(xgb_proba) - 1)].max()
        else:
            pred_str, conf = ensemble_predict(
                xgb_model, tft_model if tft_available else None,
                df.iloc[: i + 1], feature_cols
            )
            pred = {"📈 涨": 1, "➡️ 平": 0, "📉 跌": -1}.get(pred_str, 0)
        predictions.append(pred)
        confidences.append(conf)

    engine = BacktestEngine(initial_balance=10000)
    stats = engine.run(df, np.array(predictions), np.array(confidences))
    print_report(stats, symbol)

    # ── 总结 ──
    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"  ✅ 全流程完成!")
    print(f"  ⏱ 总耗时: {elapsed:.0f}秒 ({elapsed/60:.1f}分)")
    print(f"  💰 最终收益: {stats['total_return']*100:+.2f}%")
    print(f"  📈 夏普比率: {stats['sharpe_ratio']:.3f}")
    print(f"{'='*60}")

    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="量化交易全流程训练")
    parser.add_argument("--symbol", default="BTC/USDT", help="交易对")
    parser.add_argument("--no-garch", action="store_true", help="跳过高开销的 GARCH")
    args = parser.parse_args()

    pipeline(symbol=args.symbol, use_garch=not args.no_garch)
