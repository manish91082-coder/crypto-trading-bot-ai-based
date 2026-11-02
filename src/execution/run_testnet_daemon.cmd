@echo off
REM Launcher for the 1D swing engine daemon on Binance SPOT TESTNET (used by the Windows Scheduled Task).
REM The daemon logs to logs\live_1d\daemon_testnet.log itself. A second copy exits by itself
REM (single-instance lock), so the hourly task trigger works as a safe watchdog.
cd /d "E:\crypto trading bot ai based 9 oct 2026"
set PYTHONIOENCODING=utf-8
"C:\Users\Admin\AppData\Local\Programs\Python\Python312\python.exe" -u "src\execution\live_1d_swing_engine.py" --mode testnet --daemon
