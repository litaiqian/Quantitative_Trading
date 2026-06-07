package com.cryptoquant.ai.data.models

import com.google.gson.annotations.SerializedName

// ─── Auth ───
data class LoginRequest(val email: String, val password: String)
data class RegisterRequest(val username: String, val email: String, val password: String)
data class AuthResponse(val token: String, val user: User)

data class User(
    val id: Int, val username: String, val email: String,
    @SerializedName("is_admin") val isAdmin: Boolean,
    @SerializedName("subscription_tier") val subscriptionTier: String,
    @SerializedName("subscription_expires") val subscriptionExpires: String?,
)

// ─── Dashboard ───
data class Dashboard(
    @SerializedName("today_pnl") val todayPnl: Double,
    @SerializedName("today_pnl_pct") val todayPnlPct: Double,
    @SerializedName("total_trades_today") val totalTradesToday: Int,
    @SerializedName("win_rate") val winRate: Double,
    @SerializedName("total_volume") val totalVolume: Double,
    @SerializedName("total_balance") val totalBalance: Double,
    @SerializedName("active_strategies") val activeStrategies: Int,
    val balances: List<ExchangeBalance>,
)

data class ExchangeBalance(val exchange: String, val balance: Double, val error: String? = null)

// ─── Exchange ───
data class ExchangeKey(
    val id: Int, val exchange: String,
    @SerializedName("api_key") val apiKey: String,
    @SerializedName("is_active") val isActive: Boolean,
)

data class AddExchangeRequest(
    val exchange: String, @SerializedName("api_key") val apiKey: String,
    @SerializedName("api_secret") val apiSecret: String, val passphrase: String? = null,
)

// ─── Trades ───
data class TradeHistory(val trades: List<Trade>, @SerializedName("total_pnl") val totalPnl: Double)

data class Trade(
    val id: Int, val exchange: String, val symbol: String,
    val side: String, val price: Double, val amount: Double,
    val cost: Double, val pnl: Double, @SerializedName("created_at") val createdAt: String,
)

// ─── AI ───
data class TrainRequest(@SerializedName("exchange_key_id") val exchangeKeyId: Int, val symbol: String)
data class TrainResult(val status: String, @SerializedName("train_accuracy") val trainAccuracy: Double, @SerializedName("test_accuracy") val testAccuracy: Double)
data class PredictResult(val signal: String, val confidence: Double, @SerializedName("buy_probability") val buyProb: Double, @SerializedName("current_price") val currentPrice: Double, val rsi: Double?)
