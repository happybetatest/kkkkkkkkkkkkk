@echo off
title FiveM Farming Macro
cd /d "%~dp0"

echo Starting FiveM Farming Macro (Python Mode)...
python gui_macro.py

if %ERRORLEVEL% NEQ 0 (
    echo Error running macro (Exit Code: %ERRORLEVEL%)
    pause
)
