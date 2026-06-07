"""
CryptoQuant AI Platform - Database Models
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum, create_engine
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker
from datetime import datetime, timedelta
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cryptoquant.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    subscription_tier = Column(String, default="basic")  # basic / pro / enterprise
    subscription_expires = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))
    created_at = Column(DateTime, default=datetime.utcnow)

    exchange_keys = relationship("ExchangeKey", back_populates="user", cascade="all, delete")
    trading_configs = relationship("TradingConfig", back_populates="user", cascade="all, delete")
    trades = relationship("Trade", back_populates="user", cascade="all, delete")

class ExchangeKey(Base):
    __tablename__ = "exchange_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    exchange = Column(String, nullable=False)  # binance / okx / bybit
    api_key = Column(String, nullable=False)
    api_secret = Column(String, nullable=False)  # Encrypted in production
    passphrase = Column(String, nullable=True)  # For OKX
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="exchange_keys")

class TradingConfig(Base):
    __tablename__ = "trading_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    exchange_id = Column(Integer, ForeignKey("exchange_keys.id"), nullable=False)
    symbol = Column(String, nullable=False, default="BTC/USDT")
    strategy = Column(String, nullable=False, default="ml_xgboost")  # ml_xgboost / lstm / grid
    max_position_pct = Column(Float, default=0.1)  # 10% of balance per trade
    stop_loss_pct = Column(Float, default=0.05)  # 5% stop loss
    take_profit_pct = Column(Float, default=0.10)  # 10% take profit
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="trading_configs")

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    exchange = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)  # buy / sell
    order_type = Column(String, default="market")
    price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)  # price * amount
    fee = Column(Float, default=0.0)
    pnl = Column(Float, default=0.0)  # Profit/Loss
    strategy = Column(String, nullable=True)
    status = Column(String, default="filled")
    exchange_order_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="trades")

class DailyStats(Base):
    __tablename__ = "daily_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(String, nullable=False)  # YYYY-MM-DD
    pnl = Column(Float, default=0.0)
    pnl_pct = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    win_trades = Column(Integer, default=0)
    loss_trades = Column(Integer, default=0)
    total_balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
