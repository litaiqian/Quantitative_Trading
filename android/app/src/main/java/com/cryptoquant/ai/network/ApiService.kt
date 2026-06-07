package com.cryptoquant.ai.network

import com.cryptoquant.ai.data.models.*
import retrofit2.Response
import retrofit2.http.*

interface ApiService {
    // Auth
    @POST("api/auth/login")
    suspend fun login(@Body req: LoginRequest): Response<AuthResponse>

    @POST("api/auth/register")
    suspend fun register(@Body req: RegisterRequest): Response<AuthResponse>

    @GET("api/auth/me")
    suspend fun getMe(): Response<User>

    // Dashboard
    @GET("api/trading/dashboard")
    suspend fun getDashboard(): Response<Dashboard>

    // Trades
    @GET("api/trading/history")
    suspend fun getTradeHistory(@Query("days") days: Int = 7): Response<TradeHistory>

    // Exchanges
    @GET("api/exchanges/")
    suspend fun getExchanges(): Response<List<ExchangeKey>>

    @POST("api/exchanges/add")
    suspend fun addExchange(@Body req: AddExchangeRequest): Response<Map<String, Any>>

    @DELETE("api/exchanges/{id}")
    suspend fun removeExchange(@Path("id") id: Int): Response<Map<String, Any>>

    // AI
    @POST("api/trading/ai/train")
    suspend fun trainAI(@Query("exchange_key_id") keyId: Int, @Query("symbol") symbol: String): Response<TrainResult>

    @GET("api/trading/ai/predict")
    suspend fun predictAI(@Query("exchange_key_id") keyId: Int, @Query("symbol") symbol: String): Response<PredictResult>
}
