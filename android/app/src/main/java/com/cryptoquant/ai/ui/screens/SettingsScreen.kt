package com.cryptoquant.ai.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.cryptoquant.ai.network.ApiClient
import com.cryptoquant.ai.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun SettingsScreen(onLogout: () -> Unit) {
    var user by remember { mutableStateOf<com.cryptoquant.ai.data.models.User?>(null) }
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        scope.launch {
            try { val r = ApiClient.service.getMe(); if (r.isSuccessful) user = r.body() } catch (_: Exception) {}
        }
    }

    Column(Modifier.fillMaxSize().padding(16.dp)) {
        Text("⚙️ 设置", fontSize = 22.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
        Spacer(Modifier.height(16.dp))

        user?.let { u ->
            CryptoCard(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) { Text("用户名"); Text(u.username, color = TextSecondary) }
                    Spacer(Modifier.height(8.dp))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) { Text("邮箱"); Text(u.email, color = TextSecondary) }
                    Spacer(Modifier.height(8.dp))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) { Text("套餐"); Text(u.subscriptionTier.uppercase(), color = BrandPurple, fontWeight = FontWeight.Bold) }
                    Spacer(Modifier.height(8.dp))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) { Text("到期"); Text(u.subscriptionExpires ?: "-", color = TextSecondary) }
                }
            }
        }

        Spacer(Modifier.height(24.dp))
        Button(
            onClick = {
                ApiClient.setToken(null)
                onLogout()
            },
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = BrandRed),
            shape = ButtonShape,
        ) {
            Text("退出登录")
        }
    }
}
