"""
Trading Router - 交易控制 + Dashboard
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from auth import get_db, get_current_user
from database import User, ExchangeKey, TradingConfig, Trade, DailyStats

# Lazy imports for optional heavy dependencies
_ExchangeService = None
_AIStrategy = None

def _get_exchange_svc(exchange, api_key, api_secret, passphrase=None):
    global _ExchangeService
    if _ExchangeService is None:
        try:
            from services.exchange_service import ExchangeService
            _ExchangeService = ExchangeService
        except ImportError:
            raise HTTPException(503, "交易所模块未安装，运行: pip install ccxt pandas")
    return _ExchangeService(exchange, api_key, api_secret, passphrase)

def _get_ai_strategy():
    global _AIStrategy
    if _AIStrategy is None:
        try:
            from services.ai_service import AIStrategy
            _AIStrategy = AIStrategy
        except ImportError:
            raise HTTPException(503, "AI模块未安装，运行: pip install scikit-learn xgboost")
    return _AIStrategy()

router = APIRouter(prefix="/api/trading", tags=["交易"])

# 全局 AI 策略实例（按用户缓存）
ai_models = {}

class StartTradingRequest(BaseModel):
    exchange_key_id: int
    symbol: str = "BTC/USDT"
    strategy: str = "ml_xgboost"
    max_position_pct: float = 0.1
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.10

class TradingStatusResponse(BaseModel):
    is_active: bool
    configs: list = []

@router.get("/dashboard")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取今日交易概览"""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # 今日交易
    trades_today = db.query(Trade).filter(
        Trade.user_id == user.id,
        Trade.created_at >= today_start
    ).all()

    total_pnl = sum(t.pnl for t in trades_today)
    total_trades = len(trades_today)
    win_trades = sum(1 for t in trades_today if t.pnl > 0)
    loss_trades = sum(1 for t in trades_today if t.pnl < 0)
    total_volume = sum(t.cost for t in trades_today)

    # 从各交易所获取总余额
    total_balance = 0.0
    keys = db.query(ExchangeKey).filter(ExchangeKey.user_id == user.id, ExchangeKey.is_active == True).all()
    balances = []
    for k in keys:
        try:
            svc = _get_exchange_svc(k.exchange, k.api_key, k.api_secret, k.passphrase)
            bal = svc.fetch_balance()
            total_balance += bal.get("total_usdt", 0)
            balances.append({"exchange": k.exchange, "balance": round(bal.get("total_usdt", 0), 2)})
        except Exception:
            balances.append({"exchange": k.exchange, "balance": 0, "error": "获取失败"})

    # 活跃策略
    active_configs = db.query(TradingConfig).filter(
        TradingConfig.user_id == user.id, TradingConfig.is_active == True
    ).count()

    return {
        "today_pnl": round(total_pnl, 2),
        "today_pnl_pct": round(total_pnl / total_balance * 100, 2) if total_balance > 0 else 0,
        "total_trades_today": total_trades,
        "win_trades": win_trades,
        "loss_trades": loss_trades,
        "win_rate": round(win_trades / total_trades * 100, 2) if total_trades > 0 else 0,
        "total_volume": round(total_volume, 2),
        "total_balance": round(total_balance, 2),
        "balances": balances,
        "active_strategies": active_configs,
    }

@router.get("/history")
def trade_history(
    days: int = Query(7, ge=1, le=90),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取历史交易记录"""
    since = datetime.utcnow() - timedelta(days=days)
    trades = db.query(Trade).filter(
        Trade.user_id == user.id,
        Trade.created_at >= since,
    ).order_by(Trade.created_at.desc()).limit(100).all()

    return {
        "trades": [
            {
                "id": t.id,
                "exchange": t.exchange,
                "symbol": t.symbol,
                "side": t.side,
                "price": t.price,
                "amount": t.amount,
                "cost": t.cost,
                "pnl": round(t.pnl, 2),
                "fee": round(t.fee, 4),
                "created_at": t.created_at.isoformat(),
            }
            for t in trades
        ],
        "total_pnl": round(sum(t.pnl for t in trades), 2),
    }

@router.post("/ai/train")
def train_ai(
    exchange_key_id: int,
    symbol: str = "BTC/USDT",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """训练 AI 模型"""
    key = db.query(ExchangeKey).filter(ExchangeKey.id == exchange_key_id, ExchangeKey.user_id == user.id).first()
    if not key:
        raise HTTPException(404, "交易所密钥不存在")

    svc = _get_exchange_svc(key.exchange, key.api_key, key.api_secret, key.passphrase)
    df = svc.fetch_klines(symbol, "1h", 500)
    if df.empty:
        raise HTTPException(400, "获取K线数据失败")

    strategy = _get_ai_strategy()
    result = strategy.train(df)

    cache_key = f"{user.id}_{symbol}"
    ai_models[cache_key] = strategy

    return result

@router.get("/ai/predict")
def ai_predict(
    exchange_key_id: int,
    symbol: str = "BTC/USDT",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI 预测当前信号"""
    cache_key = f"{user.id}_{symbol}"
    if cache_key not in ai_models:
        raise HTTPException(400, "请先训练 AI 模型: POST /api/trading/ai/train")

    key = db.query(ExchangeKey).filter(ExchangeKey.id == exchange_key_id, ExchangeKey.user_id == user.id).first()
    if not key:
        raise HTTPException(404, "交易所密钥不存在")

    svc = _get_exchange_svc(key.exchange, key.api_key, key.api_secret, key.passphrase)
    df = svc.fetch_klines(symbol, "1h", 200)
    if df.empty:
        raise HTTPException(400, "获取K线数据失败")

    return ai_models[cache_key].predict(df)

@router.post("/start")
def start_trading(req: StartTradingRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """启动交易策略"""
    key = db.query(ExchangeKey).filter(ExchangeKey.id == req.exchange_key_id, ExchangeKey.user_id == user.id).first()
    if not key:
        raise HTTPException(404, "交易所密钥不存在")

    config = TradingConfig(
        user_id=user.id,
        exchange_id=req.exchange_key_id,
        symbol=req.symbol,
        strategy=req.strategy,
        max_position_pct=req.max_position_pct,
        stop_loss_pct=req.stop_loss_pct,
        take_profit_pct=req.take_profit_pct,
        is_active=True,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return {"id": config.id, "status": "started", "symbol": req.symbol, "strategy": req.strategy}

@router.post("/stop/{config_id}")
def stop_trading(config_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """停止策略"""
    config = db.query(TradingConfig).filter(
        TradingConfig.id == config_id, TradingConfig.user_id == user.id
    ).first()
    if not config:
        raise HTTPException(404, "策略不存在")
    config.is_active = False
    db.commit()
    return {"status": "stopped"}
