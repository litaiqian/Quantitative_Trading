"""
CryptoQuant AI Platform - Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cryptoquant.db")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production-2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24 * 7  # 7 days

# Subscription plans
PLANS = {
    "basic": {"name": "基础版", "price": 29.99, "max_exchanges": 1, "max_strategies": 1},
    "pro": {"name": "专业版", "price": 99.99, "max_exchanges": 3, "max_strategies": 5},
    "enterprise": {"name": "企业版", "price": 299.99, "max_exchanges": 10, "max_strategies": 20},
}

SUPPORTED_EXCHANGES = ["binance", "okx", "bybit"]
