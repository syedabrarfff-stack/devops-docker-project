#!/usr/bin/env python3
"""
JARVIS Council — .env Setup Wizard
Run this once in PowerShell to write your .env file correctly.
Usage: python setup_env.py
"""

import os, sys

print("\n══════════════════════════════════════════════════════")
print("  JARVIS COUNCIL — .env SETUP WIZARD")
print("══════════════════════════════════════════════════════")
print("  Paste each key when prompted. Press ENTER to skip.")
print("  Leave blank = that provider will be skipped.\n")

def ask(label, var):
    val = input(f"  {label}: ").strip()
    return var, val

keys = []

print("── AWS BEDROCK (PRIMARY SYNTHESIZER — Claude Opus 4.8) ─")
print("  This is your main synthesizer. Bedrock never expires.")
keys.append(ask("AWS_ACCESS_KEY_ID", "AWS_ACCESS_KEY_ID"))
keys.append(ask("AWS_SECRET_ACCESS_KEY", "AWS_SECRET_ACCESS_KEY"))
keys.append(ask("AWS_SESSION_TOKEN (press Enter to skip if not using temp creds)", "AWS_SESSION_TOKEN"))
region_input = input("  AWS_REGION (press Enter for us-east-1): ").strip()
keys.append(("AWS_REGION", region_input if region_input else "us-east-1"))

print("\n── BEDROCK API KEY (simplest Bedrock auth — from Getting Started page) ─")
keys.append(ask("BEDROCK_API_KEY (from Bedrock console → Getting Started → API Key, press Enter to skip)", "BEDROCK_API_KEY"))

print("\n── ANTHROPIC DIRECT (FALLBACK — only if Bedrock fails) ─")
keys.append(ask("ANTHROPIC_API_KEY (starts with sk-ant-, press Enter to skip)", "ANTHROPIC_API_KEY"))

print("\n── OPENROUTER ──────────────────────────────────────────")
keys.append(ask("OPENROUTER_API_KEY (starts with sk-or-, press Enter to skip)", "OPENROUTER_API_KEY"))

print("\n── GOOGLE ──────────────────────────────────────────────")
keys.append(ask("GOOGLE_API_KEY (starts with AIza, press Enter to skip)", "GOOGLE_API_KEY"))

print("\n── NVIDIA (ONE key works for ALL 10 models) ────────────")
nvidia = ask("NVIDIA_KEY (starts with nvapi-)", "NVIDIA_KEY_LLAMA4_MAV")[1]

lines = []
for var, val in keys:
    lines.append(f"{var}={val}")

# Fill all 10 NVIDIA slots with the same key
for slot in [
    "NVIDIA_KEY_LLAMA4_MAV", "NVIDIA_KEY_LLAMA4_SCOUT", "NVIDIA_KEY_LLAMA33",
    "NVIDIA_KEY_QWEN", "NVIDIA_KEY_KIMI", "NVIDIA_KEY_MISTRAL",
    "NVIDIA_KEY_ZAIGLAM", "NVIDIA_KEY_DEEPSEEK_V4", "NVIDIA_KEY_DEEPSEEK_PRO",
    "NVIDIA_KEY_MINIMAX",
]:
    lines.append(f"{slot}={nvidia}")

env_path = os.path.join(os.path.dirname(__file__), ".env")
with open(env_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print("\n══════════════════════════════════════════════════════")
print(f"  ✅  .env written to: {env_path}")
print("\n  Key summary:")
for var, val in keys:
    if val:
        display = val[:12] + "..." + val[-4:] if len(val) > 16 else val
        print(f"    ✅  {var}: {display} ({len(val)} chars)")
    else:
        print(f"    ⚠️   {var}: empty (will be skipped)")
if nvidia:
    print(f"    ✅  NVIDIA (all 10 slots): {nvidia[:12]}...{nvidia[-4:]} ({len(nvidia)} chars)")
else:
    print(f"    ⚠️   NVIDIA: empty (all NVIDIA models will be skipped)")
print("\n  Now run:  python council.py")
print("══════════════════════════════════════════════════════\n")
