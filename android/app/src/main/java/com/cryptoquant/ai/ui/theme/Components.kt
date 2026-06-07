package com.cryptoquant.ai.ui.theme

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.ui.Modifier
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

val CardShape = RoundedCornerShape(12.dp)
val ButtonShape = RoundedCornerShape(10.dp)
val InputShape = RoundedCornerShape(10.dp)

val CardBg = Dark800
val CardBorder = Dark700
val InputBg = Dark900
val InputBorder = Dark600

@Composable
fun CryptoCard(
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit
) {
    Surface(
        modifier = modifier,
        shape = CardShape,
        color = CardBg,
        border = BorderStroke(1.dp, CardBorder),
        content = content,
    )
}

val SectionTitle: @Composable (String) -> Unit = { title ->
    Text(
        text = title,
        style = TextStyle(fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary),
        modifier = Modifier.padding(bottom = 16.dp)
    )
}
