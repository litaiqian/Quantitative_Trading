@echo off
title CryptoQuant AI Backend
cd /d C:\Users\Administrator\crypto-quant-platform\backend
:loop
echo [%date% %time%] Starting CryptoQuant AI Backend...
python main.py
echo [%date% %time%] Backend stopped. Restarting in 3 seconds...
timeout /t 3 >nul
goto loop
