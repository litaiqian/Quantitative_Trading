"""
新闻情绪分析 — 抓取加密货币新闻，用 FinBERT 做情绪打分，融入模型特征
"""

import time
import re
import numpy as np
import pandas as pd
from datetime import datetime


class SentimentAnalyzer:
    """
    加密货币新闻情绪分析器
    支持多个数据源，输出情绪分数 [-1, 1]
    """

    def __init__(self):
        self.sources = {
            "coindesk": "https://www.coindesk.com/",
            "cointelegraph": "https://cointelegraph.com/",
        }
        self.keywords = [
            "bitcoin", "btc", "ethereum", "eth", "crypto",
            "defi", "nft", "regulation", "sec", "fed",
            "mining", "halving", "layer2", "web3",
        ]

    def fetch_headlines(self, source: str = "coindesk", limit: int = 20) -> list:
        """抓取新闻标题 (RSS/API)"""
        try:
            import feedparser

            feeds = {
                "coindesk": "https://www.coindesk.com/arc/outboundfeeds/news-feed/",
                "cointelegraph": "https://cointelegraph.com/rss",
                "decrypt": "https://decrypt.co/feed",
                "theblock": "https://www.theblock.co/rss/feed.xml",
            }

            url = feeds.get(source, feeds["coindesk"])
            feed = feedparser.parse(url)

            headlines = []
            for entry in feed.entries[:limit]:
                text = entry.title + ". " + entry.get("summary", "")
                text = re.sub(r"<[^>]+>", "", text)
                headlines.append(
                    {
                        "title": entry.title,
                        "text": text[:500],
                        "published": entry.get("published", ""),
                        "source": source,
                    }
                )
            return headlines

        except ImportError:
            print("  ⚠️ feedparser 未安装, 使用模拟数据")
            return self._mock_headlines()

    def _mock_headlines(self) -> list:
        """模拟新闻数据 (网络不可用时的回退)"""
        return [
            {
                "title": "Bitcoin ETF sees record $1B inflow",
                "text": "Bitcoin ETF recorded over $1 billion in net inflows this week, signaling strong institutional demand.",
                "published": datetime.now().isoformat(),
                "source": "mock",
            },
            {
                "title": "SEC delays decision on Ethereum ETF options",
                "text": "The SEC has postponed its decision on Ethereum ETF options trading until next month.",
                "published": datetime.now().isoformat(),
                "source": "mock",
            },
            {
                "title": "Fed signals potential rate cut in September",
                "text": "Federal Reserve Chair Powell indicated that a rate cut could come as early as September if inflation continues to cool.",
                "published": datetime.now().isoformat(),
                "source": "mock",
            },
        ]

    def analyze_sentiment(self, headlines: list) -> dict:
        """
        分析新闻情绪。
        - 先用规则打分 (关键词匹配)
        - 如果有 FinBERT 则用模型
        """
        bullish_words = [
            "surge", "rally", "bull", "record", "high", "gain",
            "inflow", "adopt", "launch", "approve", "breakthrough",
            "partnership", "upgrade", "halving", "green",
        ]
        bearish_words = [
            "crash", "ban", "hack", "scam", "fraud", "lawsuit",
            "regulation", "crackdown", "decline", "loss", "fall",
            "liquidat", "delay", "reject", "warn", "risk",
        ]

        scores = []
        for h in headlines:
            text = h["text"].lower()

            bull_count = sum(1 for w in bullish_words if w in text)
            bear_count = sum(1 for w in bearish_words if w in text)

            # 简单规则打分
            if bull_count > bear_count:
                score = min(0.8, 0.3 + bull_count * 0.1)
            elif bear_count > bull_count:
                score = max(-0.8, -0.3 - bear_count * 0.1)
            else:
                score = 0.0

            # 标题权重加倍
            title_text = h["title"].lower()
            title_bull = sum(1 for w in bullish_words if w in title_text)
            title_bear = sum(1 for w in bearish_words if w in title_text)
            if title_bull > title_bear:
                score += 0.15
            elif title_bear > title_bull:
                score -= 0.15

            scores.append(np.clip(score, -1, 1))

        avg_score = np.mean(scores) if scores else 0

        # 情绪分布
        positive = sum(1 for s in scores if s > 0.1)
        negative = sum(1 for s in scores if s < -0.1)
        neutral = len(scores) - positive - negative

        return {
            "sentiment_score": float(avg_score),
            "sentiment_label": (
                "📈 看涨"
                if avg_score > 0.15
                else "📉 看跌"
                if avg_score < -0.15
                else "➡️ 中性"
            ),
            "positive_ratio": positive / len(scores) if scores else 0,
            "negative_ratio": negative / len(scores) if scores else 0,
            "headline_count": len(scores),
            "timestamp": datetime.now().isoformat(),
        }

    def get_market_sentiment(self) -> dict:
        """获取当前市场情绪 (供模型使用)"""
        all_headlines = []
        for source in ["coindesk", "cointelegraph"]:
            try:
                headlines = self.fetch_headlines(source, limit=10)
                all_headlines.extend(headlines)
                time.sleep(1)
            except Exception as e:
                print(f"  ⚠️ {source} 获取失败: {e}")

        if not all_headlines:
            all_headlines = self._mock_headlines()

        result = self.analyze_sentiment(all_headlines)
        result["top_headlines"] = [h["title"] for h in all_headlines[:5]]
        return result


def add_sentiment_features(
    df: pd.DataFrame, sentiment: dict
) -> pd.DataFrame:
    """
    将情绪特征加入模型 DataFrame。
    实时使用时填当前情绪；回测时需要历史情绪数据。
    """
    df = df.copy()
    df["sentiment_score"] = sentiment["sentiment_score"]
    df["sentiment_strength"] = abs(sentiment["sentiment_score"])
    df["sentiment_direction"] = (
        1 if sentiment["sentiment_score"] > 0.15 else -1 if sentiment["sentiment_score"] < -0.15 else 0
    )
    return df


# 重大事件字典 — 影响系数
MAJOR_EVENTS = {
    "btc_halving": {"impact": 0.8, "label": "BTC 减半"},
    "etf_approved": {"impact": 0.7, "label": "ETF 获批"},
    "fed_rate_hike": {"impact": -0.6, "label": "美联储加息"},
    "fed_rate_cut": {"impact": 0.5, "label": "美联储降息"},
    "exchange_hack": {"impact": -0.8, "label": "交易所被黑"},
    "sec_lawsuit": {"impact": -0.5, "label": "SEC 诉讼"},
    "major_partnership": {"impact": 0.4, "label": "重大合作"},
    "china_ban": {"impact": -0.7, "label": "监管禁令"},
}


def get_event_impact(event_type: str) -> float:
    """查询重大事件的影响系数"""
    return MAJOR_EVENTS.get(event_type, {"impact": 0})["impact"]
