@echo off
title FiveM Farming Macro [BETA]
cd /d "%~dp0"
set FIVEM_FARMING_CHANNEL=beta

echo Starting FiveM Farming Macro [BETA] (Python Mode)...
python gui_macro.py

if %ERRORLEVEL% NEQ 0 (
    echo Error running macro (Exit Code: %ERRORLEVEL%)
    pause
)
