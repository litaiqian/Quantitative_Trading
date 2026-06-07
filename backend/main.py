"""
CryptoQuant AI Platform - Main Entry
一个商用级 AI 量化交易 SaaS 平台
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routers import auth_router, exchange_router, trading_router, admin_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("🚀 CryptoQuant AI Platform started")
    yield

app = FastAPI(
    title="CryptoQuant AI",
    description="AI 量化交易平台 - 支持币安/OKX/Bybit",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(exchange_router.router)
app.include_router(trading_router.router)
app.include_router(admin_router.router)

@app.get("/")
def root():
    return {
        "name": "CryptoQuant AI",
        "version": "1.0.0",
        "docs": "/docs",
        "exchanges": ["binance", "okx", "bybit"],
    }

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
