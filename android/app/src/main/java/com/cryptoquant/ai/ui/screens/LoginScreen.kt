package com.cryptoquant.ai.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.cryptoquant.ai.data.models.LoginRequest
import com.cryptoquant.ai.data.models.RegisterRequest
import com.cryptoquant.ai.network.ApiClient
import com.cryptoquant.ai.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun LoginScreen(onLoginSuccess: (String) -> Unit) {
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var username by remember { mutableStateOf("") }
    var isRegister by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var loading by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(listOf(Dark900, Dark800, Dark700))
            ),
        contentAlignment = Alignment.Center,
    ) {
        Card(
            modifier = Modifier
                .padding(24.dp)
                .widthIn(max = 400.dp),
            shape = CardShape,
            colors = CardDefaults.cardColors(containerColor = Dark800),
            border = BorderStroke(1.dp, Dark700),
        ) {
            Column(
                modifier = Modifier.padding(32.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text("⚡", fontSize = 40.sp)
                Spacer(Modifier.height(8.dp))
                Text(
                    "CryptoQuant AI",
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    color = BrandBlue,
                )
                Text("AI 量化交易平台", color = TextMuted, fontSize = 13.sp)
                Spacer(Modifier.height(24.dp))

                if (error != null) {
                    Text(error!!, color = BrandRed, fontSize = 13.sp)
                    Spacer(Modifier.height(8.dp))
                }

                if (isRegister) {
                    OutlinedTextField(
                        value = username, onValueChange = { username = it },
                        label = { Text("用户名") }, singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                        shape = InputShape,
                        colors = inputColors(),
                    )
                    Spacer(Modifier.height(8.dp))
                }

                OutlinedTextField(
                    value = email, onValueChange = { email = it },
                    label = { Text("邮箱") }, singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                    modifier = Modifier.fillMaxWidth(),
                    shape = InputShape,
                    colors = inputColors(),
                )
                Spacer(Modifier.height(8.dp))

                OutlinedTextField(
                    value = password, onValueChange = { password = it },
                    label = { Text("密码") }, singleLine = true,
                    visualTransformation = PasswordVisualTransformation(),
                    modifier = Modifier.fillMaxWidth(),
                    shape = InputShape,
                    colors = inputColors(),
                )
                Spacer(Modifier.height(16.dp))

                Button(
                    onClick = {
                        loading = true; error = null
                        scope.launch {
                            try {
                                val res = if (isRegister) {
                                    ApiClient.service.register(RegisterRequest(username, email, password))
                                } else {
                                    ApiClient.service.login(LoginRequest(email, password))
                                }
                                if (res.isSuccessful) {
                                    res.body()?.let {
                                        ApiClient.setToken(it.token)
                                        onLoginSuccess(it.token)
                                    }
                                } else {
                                    error = res.errorBody()?.string() ?: "登录失败"
                                }
                            } catch (e: Exception) {
                                error = "网络错误: ${e.message}"
                            }
                            loading = false
                        }
                    },
                    enabled = !loading,
                    modifier = Modifier.fillMaxWidth().height(50.dp),
                    shape = ButtonShape,
                    colors = ButtonDefaults.buttonColors(containerColor = BrandBlue),
                ) {
                    if (loading) CircularProgressIndicator(modifier = Modifier.size(20.dp), color = TextPrimary)
                    else Text(if (isRegister) "注册" else "登录", fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
                }

                Spacer(Modifier.height(12.dp))
                TextButton(onClick = { isRegister = !isRegister; error = null }) {
                    Text(
                        if (isRegister) "已有账号？登录" else "没有账号？注册",
                        color = TextSecondary, fontSize = 13.sp,
                    )
                }
            }
        }
    }
}

@Composable
internal fun inputColors() = OutlinedTextFieldDefaults.colors(
    focusedBorderColor = BrandBlue,
    unfocusedBorderColor = Dark600,
    focusedLabelColor = BrandBlue,
    unfocusedLabelColor = TextMuted,
    cursorColor = BrandBlue,
    focusedTextColor = TextPrimary,
    unfocusedTextColor = TextPrimary,
    focusedContainerColor = Dark900,
    unfocusedContainerColor = Dark900,
)
