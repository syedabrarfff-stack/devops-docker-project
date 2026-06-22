#!/usr/bin/env python3
"""Quick test — checks keys are loaded and tests one call per provider."""

import asyncio, os, sys

try:
    import httpx
except ImportError:
    import subprocess; subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "-q"]); import httpx

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    import subprocess; subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv", "-q"])
    from dotenv import load_dotenv; load_dotenv()

ANTHROPIC_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
NVIDIA_KEY     = os.getenv("NVIDIA_KEY_LLAMA33", "")

print("\n══════════════════════════════════════")
print("  JARVIS COUNCIL — KEY DIAGNOSTIC")
print("══════════════════════════════════════\n")

def show(name, key):
    if not key:
        print(f"  ❌  {name}: NOT LOADED (empty)")
    else:
        print(f"  ✅  {name}: {key[:12]}...{key[-4:]} ({len(key)} chars)")

show("ANTHROPIC_API_KEY", ANTHROPIC_KEY)
show("OPENROUTER_API_KEY", OPENROUTER_KEY)
show("NVIDIA_KEY_LLAMA33", NVIDIA_KEY)
print()

async def test():
    async with httpx.AsyncClient() as client:

        # Test NVIDIA
        print("── Testing NVIDIA (Llama 3.3 70B)...")
        if NVIDIA_KEY:
            try:
                r = await client.post(
                    "https://integrate.api.nvidia.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {NVIDIA_KEY}", "Content-Type": "application/json"},
                    json={"model": "meta/llama-3.3-70b-instruct",
                          "messages": [{"role": "user", "content": "Say OK"}],
                          "max_tokens": 5},
                    timeout=30.0,
                )
                if r.status_code == 200:
                    print(f"  ✅  NVIDIA: SUCCESS — {r.json()['choices'][0]['message']['content'][:50]}")
                else:
                    print(f"  ❌  NVIDIA: HTTP {r.status_code} — {r.text[:200]}")
            except Exception as e:
                print(f"  ❌  NVIDIA: {str(e)[:200]}")
        else:
            print("  ❌  NVIDIA: key not loaded")

        # Test Anthropic
        print("\n── Testing Anthropic (Claude Sonnet 4.6)...")
        if ANTHROPIC_KEY:
            try:
                r = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01",
                             "Content-Type": "application/json"},
                    json={"model": "claude-sonnet-4-6", "max_tokens": 5,
                          "messages": [{"role": "user", "content": "Say OK"}]},
                    timeout=30.0,
                )
                if r.status_code == 200:
                    print(f"  ✅  ANTHROPIC: SUCCESS — {r.json()['content'][0]['text'][:50]}")
                else:
                    print(f"  ❌  ANTHROPIC: HTTP {r.status_code} — {r.text[:300]}")
            except Exception as e:
                print(f"  ❌  ANTHROPIC: {str(e)[:200]}")
        else:
            print("  ❌  ANTHROPIC: key not loaded")

        # Test OpenRouter
        print("\n── Testing OpenRouter (Jamba)...")
        if OPENROUTER_KEY:
            try:
                r = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENROUTER_KEY}",
                             "Content-Type": "application/json",
                             "HTTP-Referer": "https://aliyarsolutions.com"},
                    json={"model": "ai21/jamba-1-5-large",
                          "messages": [{"role": "user", "content": "Say OK"}],
                          "max_tokens": 5},
                    timeout=30.0,
                )
                if r.status_code == 200:
                    print(f"  ✅  OPENROUTER: SUCCESS — {r.json()['choices'][0]['message']['content'][:50]}")
                else:
                    print(f"  ❌  OPENROUTER: HTTP {r.status_code} — {r.text[:200]}")
            except Exception as e:
                print(f"  ❌  OPENROUTER: {str(e)[:200]}")
        else:
            print("  ❌  OPENROUTER: key not loaded")

    print("\n══════════════════════════════════════\n")

asyncio.run(test())
