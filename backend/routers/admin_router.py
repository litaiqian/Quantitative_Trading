"""
Admin Router - 管理员后台
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from auth import get_db, get_admin_user
from database import User, Trade, DailyStats, TradingConfig
from config import PLANS

router = APIRouter(prefix="/api/admin", tags=["管理后台"])

@router.get("/users")
def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """用户列表"""
    total = db.query(User).count()
    users = db.query(User).order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return {
        "total": total,
        "page": page,
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "is_admin": u.is_admin,
                "is_active": u.is_active,
                "subscription_tier": u.subscription_tier,
                "subscription_expires": u.subscription_expires.isoformat() if u.subscription_expires else None,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ]
    }

@router.get("/stats")
def platform_stats(admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """平台统计"""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    total_trades = db.query(Trade).count()

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_trades = db.query(Trade).filter(Trade.created_at >= today).count()

    # 订阅分布
    basic = db.query(User).filter(User.subscription_tier == "basic").count()
    pro = db.query(User).filter(User.subscription_tier == "pro").count()
    enterprise = db.query(User).filter(User.subscription_tier == "enterprise").count()

    monthly_revenue = basic * PLANS["basic"]["price"] + pro * PLANS["pro"]["price"] + enterprise * PLANS["enterprise"]["price"]

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_trades": total_trades,
        "today_trades": today_trades,
        "subscriptions": {"basic": basic, "pro": pro, "enterprise": enterprise},
        "estimated_monthly_revenue": round(monthly_revenue, 2),
    }

@router.put("/users/{user_id}/toggle")
def toggle_user(user_id: int, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    """启用/禁用用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    user.is_active = not user.is_active
    db.commit()
    return {"id": user.id, "is_active": user.is_active}

@router.put("/users/{user_id}/subscription")
def set_subscription(
    user_id: int,
    tier: str,
    days: int = 30,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """设置用户订阅"""
    if tier not in PLANS:
        raise HTTPException(400, f"无效套餐: {tier}，可选: {list(PLANS.keys())}")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    user.subscription_tier = tier
    user.subscription_expires = datetime.utcnow() + timedelta(days=days)
    db.commit()
    return {"id": user.id, "tier": tier, "expires": user.subscription_expires.isoformat()}
