@echo off
cd /d C:\Users\Administrator\crypto-quant-platform
echo Pushing to GitHub...
git remote set-url origin https://github.com/litaiqian/Quantitative_Trading.git
git push -u origin master
echo Done! Check: https://github.com/litaiqian/Quantitative_Trading/actions
pause
