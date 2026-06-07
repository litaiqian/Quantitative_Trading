package com.cryptoquant.ai.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.cryptoquant.ai.data.models.AddExchangeRequest
import com.cryptoquant.ai.data.models.ExchangeKey
import com.cryptoquant.ai.network.ApiClient
import com.cryptoquant.ai.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun ExchangeScreen() {
    var exchanges by remember { mutableStateOf<List<ExchangeKey>>(emptyList()) }
    var showDialog by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    fun refresh() {
        scope.launch {
            try { val r = ApiClient.service.getExchanges(); if (r.isSuccessful) exchanges = r.body()!! } catch (_: Exception) {}
        }
    }

    LaunchedEffect(Unit) { refresh() }

    LazyColumn(modifier = Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("🔗 交易所", fontSize = 22.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                IconButton(onClick = { showDialog = true }) {
                    Icon(Icons.Default.Add, "添加", tint = BrandBlue)
                }
            }
        }

        if (exchanges.isEmpty()) {
            item {
                Box(Modifier.fillMaxWidth().padding(40.dp), contentAlignment = androidx.compose.ui.Alignment.Center) {
                    Text("未添加交易所", color = TextMuted)
                }
            }
        }

        items(exchanges) { ex ->
            CryptoCard(modifier = Modifier.fillMaxWidth()) {
                Row(Modifier.fillMaxWidth().padding(14.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                    Column {
                        Text(ex.exchange.uppercase(), fontWeight = FontWeight.Bold, color = TextPrimary)
                        Text(ex.apiKey, fontSize = 11.sp, color = TextMuted)
                    }
                    IconButton(onClick = {
                        scope.launch {
                            try { ApiClient.service.removeExchange(ex.id); refresh() } catch (_: Exception) {}
                        }
                    }) {
                        Icon(Icons.Default.Delete, "删除", tint = BrandRed)
                    }
                }
            }
        }
    }

    if (showDialog) AddExchangeDialog(onDismiss = { showDialog = false }, onAdded = { showDialog = false; refresh() })
}

@Composable
private fun AddExchangeDialog(onDismiss: () -> Unit, onAdded: () -> Unit) {
    var exchange by remember { mutableStateOf("binance") }
    var apiKey by remember { mutableStateOf("") }
    var secret by remember { mutableStateOf("") }
    var passphrase by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = Dark800,
        title = { Text("添加交易所", color = TextPrimary) },
        text = {
            Column {
                // Exchange selector as 3 buttons
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("binance" to "币安", "okx" to "OKX", "bybit" to "Bybit").forEach { (id, name) ->
                        FilterChip(
                            selected = exchange == id,
                            onClick = { exchange = id },
                            label = { Text(name, fontSize = 12.sp) },
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = BrandBlue,
                                selectedLabelColor = TextPrimary,
                            ),
                        )
                    }
                }
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(apiKey, { apiKey = it }, label = { Text("API Key") }, singleLine = true, modifier = Modifier.fillMaxWidth(), shape = InputShape, colors = inputColors())
                Spacer(Modifier.height(4.dp))
                OutlinedTextField(secret, { secret = it }, label = { Text("API Secret") }, singleLine = true, modifier = Modifier.fillMaxWidth(), shape = InputShape, colors = inputColors())
                if (exchange == "okx") {
                    Spacer(Modifier.height(4.dp))
                    OutlinedTextField(passphrase, { passphrase = it }, label = { Text("Passphrase") }, singleLine = true, modifier = Modifier.fillMaxWidth(), shape = InputShape, colors = inputColors())
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    loading = true
                    scope.launch {
                        try {
                            ApiClient.service.addExchange(AddExchangeRequest(exchange, apiKey, secret, passphrase.ifBlank { null }))
                            onAdded()
                        } catch (_: Exception) {}
                        loading = false
                    }
                },
                enabled = apiKey.isNotBlank() && secret.isNotBlank() && !loading,
                colors = ButtonDefaults.buttonColors(containerColor = BrandBlue),
            ) { Text(if (loading) "..." else "添加") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("取消", color = TextSecondary) } },
    )
}
