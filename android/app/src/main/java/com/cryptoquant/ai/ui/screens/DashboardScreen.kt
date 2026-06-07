package com.cryptoquant.ai.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.cryptoquant.ai.data.models.Dashboard
import com.cryptoquant.ai.network.ApiClient
import com.cryptoquant.ai.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun DashboardScreen() {
    var data by remember { mutableStateOf<Dashboard?>(null) }
    var loading by remember { mutableStateOf(true) }
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        scope.launch {
            try {
                val res = ApiClient.service.getDashboard()
                if (res.isSuccessful) data = res.body()
            } catch (_: Exception) {}
            loading = false
        }
    }

    if (loading) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator(color = BrandBlue)
        }
        return
    }

    val d = data ?: return

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item { Text("📊 仪表盘", fontSize = 22.sp, fontWeight = FontWeight.Bold, color = TextPrimary) }

        // Stats Grid
        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StatCard("今日盈亏", "$${fmt(d.todayPnl)}", "${d.todayPnlPct}%", Icons.Default.TrendingUp, if (d.todayPnl >= 0) BrandGreen else BrandRed, Modifier.weight(1f))
                StatCard("交易次数", "${d.totalTradesToday}", "胜率 ${d.winRate}%", Icons.Default.BarChart, BrandCyan, Modifier.weight(1f))
            }
        }
        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StatCard("总资产", "$${fmt(d.totalBalance)}", "${d.activeStrategies} 策略", Icons.Default.AccountBalance, BrandPurple, Modifier.weight(1f))
                StatCard("交易量", "$${fmt(d.totalVolume)}", "今日累计", Icons.Default.ShowChart, BrandBlue, Modifier.weight(1f))
            }
        }

        // Strategy Status
        item {
            CryptoCard(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                Column(Modifier.padding(16.dp)) {
                    SectionTitle("🤖 AI 策略")
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("活跃策略", color = TextSecondary)
                        Text("${d.activeStrategies} 个", color = BrandGreen, fontWeight = FontWeight.Bold)
                    }
                    Spacer(Modifier.height(4.dp))
                    LinearProgressIndicator(
                        progress = { (d.activeStrategies / 10f).coerceIn(0f, 1f) },
                        modifier = Modifier.fillMaxWidth().height(6.dp),
                        color = BrandBlue,
                        trackColor = Dark700,
                    )
                }
            }
        }

        // Balances
        if (d.balances.isNotEmpty()) {
            item {
                CryptoCard(modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp)) {
                        SectionTitle("💰 资产分布")
                        d.balances.forEach { bal ->
                            Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text(bal.exchange.uppercase(), color = TextSecondary, fontWeight = FontWeight.Medium)
                                Text("$${fmt(bal.balance)}", color = BrandGreen, fontWeight = FontWeight.Bold)
                            }
                            if (bal != d.balances.last()) Divider(color = Dark700, thickness = 0.5.dp)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun StatCard(label: String, value: String, sub: String, icon: ImageVector, accent: Color, modifier: Modifier = Modifier) {
    CryptoCard(modifier = modifier) {
        Column(Modifier.padding(14.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
                Text(label, color = TextMuted, fontSize = 11.sp)
                Icon(icon, contentDescription = null, tint = accent, modifier = Modifier.size(20.dp))
            }
            Spacer(Modifier.height(6.dp))
            Text(value, fontSize = 20.sp, fontWeight = FontWeight.Bold, color = accent)
            Text(sub, color = TextMuted, fontSize = 11.sp)
        }
    }
}

private fun fmt(n: Double): String {
    return if (n >= 1_000_000) "%.1fM".format(n / 1_000_000)
    else if (n >= 1_000) "%.1fK".format(n / 1_000)
    else "%.2f".format(n)
}
