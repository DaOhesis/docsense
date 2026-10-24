@echo off
title DocSense Launcher
echo ============================================================
echo         Starting DocSense (API + Streamlit Review UI)
echo ============================================================
echo.

IF EXIST ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run.py
) ELSE (
    python run.py
)

pause
