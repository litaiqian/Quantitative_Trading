"""
Exchange Keys Router - 交易所密钥管理
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from auth import get_db, get_current_user
from database import User, ExchangeKey
from config import SUPPORTED_EXCHANGES

router = APIRouter(prefix="/api/exchanges", tags=["交易所"])

class AddExchangeKeyRequest(BaseModel):
    exchange: str  # binance / okx / bybit
    api_key: str
    api_secret: str
    passphrase: str = None  # OKX 需要

class ExchangeKeyResponse(BaseModel):
    id: int
    exchange: str
    api_key: str  # 只显示前8后4位
    is_active: bool

    class Config:
        from_attributes = True

@router.get("/supported")
def supported_exchanges():
    return {"exchanges": SUPPORTED_EXCHANGES}

@router.get("/", response_model=list[ExchangeKeyResponse])
def list_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    keys = db.query(ExchangeKey).filter(ExchangeKey.user_id == user.id).all()
    result = []
    for k in keys:
        masked = k.api_key[:8] + "****" + k.api_key[-4:] if len(k.api_key) > 12 else "****"
        result.append(ExchangeKeyResponse(id=k.id, exchange=k.exchange, api_key=masked, is_active=k.is_active))
    return result

@router.post("/add")
def add_key(req: AddExchangeKeyRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if req.exchange not in SUPPORTED_EXCHANGES:
        raise HTTPException(400, f"不支持的交易所: {req.exchange}，支持: {SUPPORTED_EXCHANGES}")
    # 检查该交易所是否已添加
    existing = db.query(ExchangeKey).filter(
        ExchangeKey.user_id == user.id, ExchangeKey.exchange == req.exchange
    ).first()
    if existing:
        raise HTTPException(400, f"{req.exchange} 已添加，请先删除再重新添加")

    key = ExchangeKey(
        user_id=user.id,
        exchange=req.exchange,
        api_key=req.api_key,
        api_secret=req.api_secret,
        passphrase=req.passphrase,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return {"id": key.id, "exchange": key.exchange, "status": "added"}

@router.delete("/{key_id}")
def remove_key(key_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    key = db.query(ExchangeKey).filter(ExchangeKey.id == key_id, ExchangeKey.user_id == user.id).first()
    if not key:
        raise HTTPException(404, "密钥不存在")
    db.delete(key)
    db.commit()
    return {"status": "deleted"}
