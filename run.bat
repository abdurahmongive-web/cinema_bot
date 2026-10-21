@echo off
chcp 65001 > nul
echo =======================================
echo     Запуск AI Кино-Бота в Telegram    
echo =======================================
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python main.py
pause
