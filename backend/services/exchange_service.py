"""
Multi-Exchange API Service (Binance / OKX / Bybit)
"""
from __future__ import annotations
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

# Lazy imports - installed on demand
ccxt = None
pd = None

def _ensure_ccxt():
    global ccxt, pd
    if ccxt is None:
        import importlib
        try:
            ccxt = importlib.import_module("ccxt")
            pd = importlib.import_module("pandas")
        except ImportError:
            raise ImportError("请先安装 ccxt 和 pandas: pip install ccxt pandas")

class ExchangeService:
    """Unified interface for Binance, OKX, Bybit"""

    def __init__(self, exchange: str, api_key: str, api_secret: str, passphrase: str = None):
        _ensure_ccxt()
        _exchange_classes = {
            "binance": ccxt.binance,
            "okx": ccxt.okx,
            "bybit": ccxt.bybit,
        }
        if exchange not in _exchange_classes:
            raise ValueError(f"不支持的交易所: {exchange}")
        params = {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        }
        if exchange == "okx" and passphrase:
            params["password"] = passphrase
        self.exchange = _exchange_classes[exchange](params)
        self.name = exchange

    def fetch_balance(self) -> Dict:
        """获取账户余额"""
        try:
            balance = self.exchange.fetch_balance()
            total_usdt = balance.get("total", {}).get("USDT", 0)
            return {"total_usdt": total_usdt, "free_usdt": balance.get("free", {}).get("USDT", 0)}
        except Exception as e:
            return {"error": str(e), "total_usdt": 0}

    def fetch_klines(self, symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 500) -> pd.DataFrame:
        """获取 K 线数据"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            return df
        except Exception as e:
            return pd.DataFrame()

    def get_current_price(self, symbol: str = "BTC/USDT") -> float:
        """获取当前价格"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker["last"]
        except Exception:
            return 0.0

    def place_order(self, symbol: str, side: str, amount: float, price: float = None) -> Dict:
        """下单：市价或限价"""
        try:
            if price:
                order = self.exchange.create_limit_order(symbol, side, amount, price)
            else:
                order = self.exchange.create_market_order(symbol, side, amount)
            return {
                "order_id": order.get("id"),
                "symbol": symbol,
                "side": side,
                "price": order.get("price") or order.get("average", 0),
                "amount": order.get("amount") or amount,
                "cost": order.get("cost", 0),
                "fee": order.get("fee", {}).get("cost", 0) if order.get("fee") else 0,
                "status": order.get("status", "unknown"),
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def get_open_orders(self, symbol: str = None) -> list:
        """获取未成交订单"""
        try:
            return self.exchange.fetch_open_orders(symbol)
        except Exception:
            return []

    def cancel_all_orders(self, symbol: str = None):
        """取消所有订单"""
        try:
            return self.exchange.cancel_all_orders(symbol)
        except Exception:
            return []
