package com.cryptoquant.ai

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.cryptoquant.ai.ui.screens.*
import com.cryptoquant.ai.ui.theme.*

sealed class Screen(val route: String, val title: String, val icon: ImageVector) {
    object Dashboard : Screen("dashboard", "仪表盘", Icons.Default.Dashboard)
    object Exchange : Screen("exchange", "交易所", Icons.Default.AccountBalanceWallet)
    object Settings : Screen("settings", "设置", Icons.Default.Settings)
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            CryptoQuantTheme {
                var isLoggedIn by remember { mutableStateOf(false) }
                var currentScreen by remember { mutableStateOf<Screen>(Screen.Dashboard) }

                if (!isLoggedIn) {
                    LoginScreen(onLoginSuccess = { isLoggedIn = true })
                } else {
                    Scaffold(
                        containerColor = Dark900,
                        bottomBar = {
                            NavigationBar(containerColor = Dark800, tonalElevation = 0.dp) {
                                listOf(Screen.Dashboard, Screen.Exchange, Screen.Settings).forEach { screen ->
                                    NavigationBarItem(
                                        selected = currentScreen == screen,
                                        onClick = { currentScreen = screen },
                                        icon = { Icon(screen.icon, contentDescription = screen.title) },
                                        label = { Text(screen.title, fontSize = 11.sp) },
                                        colors = NavigationBarItemDefaults.colors(
                                            selectedIconColor = BrandBlue,
                                            selectedTextColor = BrandBlue,
                                            unselectedIconColor = TextMuted,
                                            unselectedTextColor = TextMuted,
                                            indicatorColor = Dark700,
                                        ),
                                    )
                                }
                            }
                        }
                    ) { padding ->
                        Box(Modifier.padding(padding)) {
                            when (currentScreen) {
                                Screen.Dashboard -> DashboardScreen()
                                Screen.Exchange -> ExchangeScreen()
                                Screen.Settings -> SettingsScreen(onLogout = { isLoggedIn = false })
                            }
                        }
                    }
                }
            }
        }
    }
}
