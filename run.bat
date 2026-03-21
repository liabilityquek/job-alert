@echo off
:: Job Alert System — Windows launcher
:: Double-click this file OR run from Task Scheduler

cd /d "%~dp0"
echo [%DATE% %TIME%] Starting Job Alert System...
python main.py
echo [%DATE% %TIME%] Done.
pause
