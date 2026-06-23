@echo off
:: ═══════════════════════════════════════════════════════════════
::  JARVIS COUNCIL — ONE-CLICK SETUP
::  INSTRUCTIONS:
::  1. Open this file in Notepad
::  2. Replace every PASTE_YOUR_..._HERE with your actual key
::  3. Save the file
::  4. Double-click to run
::  5. Then run: python council.py
:: ═══════════════════════════════════════════════════════════════

cd /d "%~dp0"

echo Creating .env file...

(
echo AWS_ACCESS_KEY_ID=PASTE_YOUR_AWS_ACCESS_KEY_HERE
echo AWS_SECRET_ACCESS_KEY=PASTE_YOUR_AWS_SECRET_KEY_HERE
echo AWS_SESSION_TOKEN=
echo AWS_REGION=ap-south-1
echo AWS_BEARER_TOKEN_BEDROCK=PASTE_YOUR_BEDROCK_ABSK_KEY_HERE
echo ANTHROPIC_API_KEY=PASTE_YOUR_SK_ANT_KEY_HERE
echo OPENROUTER_API_KEY=PASTE_YOUR_SK_OR_KEY_HERE
echo GOOGLE_API_KEY=PASTE_YOUR_GOOGLE_AIza_KEY_HERE
echo NVIDIA_KEY_LLAMA4_MAV=PASTE_YOUR_NVAPI_KEY_HERE
echo NVIDIA_KEY_LLAMA4_SCOUT=PASTE_YOUR_NVAPI_KEY_HERE
echo NVIDIA_KEY_LLAMA33=PASTE_YOUR_NVAPI_KEY_HERE
echo NVIDIA_KEY_QWEN=PASTE_YOUR_NVAPI_KEY_HERE
echo NVIDIA_KEY_KIMI=PASTE_YOUR_NVAPI_KEY_HERE
echo NVIDIA_KEY_MISTRAL=PASTE_YOUR_NVAPI_KEY_HERE
echo NVIDIA_KEY_ZAIGLAM=PASTE_YOUR_NVAPI_KEY_HERE
echo NVIDIA_KEY_DEEPSEEK_V4=PASTE_YOUR_NVAPI_KEY_HERE
echo NVIDIA_KEY_DEEPSEEK_PRO=PASTE_YOUR_NVAPI_KEY_HERE
echo NVIDIA_KEY_MINIMAX=PASTE_YOUR_NVAPI_KEY_HERE
) > .env

echo.
echo ✅ .env file created at: %~dp0.env
echo.
echo Now run:  python council.py
echo.
pause
