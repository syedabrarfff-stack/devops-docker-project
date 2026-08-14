@echo off
:: ═══════════════════════════════════════════════════════════════
::  JARVIS AI Council — Quick Launch
::  Double-click this file to start the council.
::  Make sure you have filled in council\.env with your API keys.
:: ═══════════════════════════════════════════════════════════════
cd /d "%~dp0"

echo.
echo  Checking dependencies...
pip install -r requirements.txt -q
echo  Dependencies OK.
echo.

python council.py
pause
