#!/usr/bin/env python3
"""
JARVIS Council — Full Diagnostic
Run this to see exactly which providers and models are working.
Usage: python test_keys.py
"""

import asyncio
import os
import sys

def install(pkg):
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

try:
    import httpx
except ImportError:
    install("httpx"); import httpx

_ENV = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

try:
    from dotenv import load_dotenv
    load_dotenv(_ENV)
except ImportError:
    install("python-dotenv")
    from dotenv import load_dotenv; load_dotenv(_ENV)

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    G = Fore.GREEN; R = Fore.RED; Y = Fore.YELLOW; C = Fore.CYAN; B = Style.BRIGHT; RS = Style.RESET_ALL
except ImportError:
    install("colorama")
    from colorama import Fore, Style, init; init(autoreset=True)
    G = Fore.GREEN; R = Fore.RED; Y = Fore.YELLOW; C = Fore.CYAN; B = Style.BRIGHT; RS = Style.RESET_ALL


# ── Load all keys ────────────────────────────────────────────────────────────

ANTHROPIC_KEY     = os.getenv("ANTHROPIC_API_KEY", "")
OPENROUTER_KEY    = os.getenv("OPENROUTER_API_KEY", "")
GOOGLE_KEY        = os.getenv("GOOGLE_API_KEY", "")
BEDROCK_API_KEY   = os.getenv("AWS_BEARER_TOKEN_BEDROCK", "")
AWS_ACCESS_KEY    = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_KEY    = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION        = os.getenv("AWS_REGION", "ap-south-1")
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN", "")

NV_KEYS = {
    "NVIDIA_KEY_LLAMA4_MAV":   os.getenv("NVIDIA_KEY_LLAMA4_MAV", ""),
    "NVIDIA_KEY_LLAMA4_SCOUT": os.getenv("NVIDIA_KEY_LLAMA4_SCOUT", ""),
    "NVIDIA_KEY_LLAMA33":      os.getenv("NVIDIA_KEY_LLAMA33", ""),
    "NVIDIA_KEY_QWEN":         os.getenv("NVIDIA_KEY_QWEN", ""),
    "NVIDIA_KEY_KIMI":         os.getenv("NVIDIA_KEY_KIMI", ""),
    "NVIDIA_KEY_MISTRAL":      os.getenv("NVIDIA_KEY_MISTRAL", ""),
    "NVIDIA_KEY_ZAIGLAM":      os.getenv("NVIDIA_KEY_ZAIGLAM", ""),
    "NVIDIA_KEY_DEEPSEEK_V4":  os.getenv("NVIDIA_KEY_DEEPSEEK_V4", ""),
    "NVIDIA_KEY_DEEPSEEK_PRO": os.getenv("NVIDIA_KEY_DEEPSEEK_PRO", ""),
    "NVIDIA_KEY_MINIMAX":      os.getenv("NVIDIA_KEY_MINIMAX", ""),
}

NVIDIA_MODELS = {
    "NVIDIA_KEY_LLAMA4_MAV":   "meta/llama-4-maverick-17b-128e-instruct",
    "NVIDIA_KEY_LLAMA4_SCOUT": "meta/llama-4-scout-17b-16e-instruct",
    "NVIDIA_KEY_LLAMA33":      "meta/llama-3.3-70b-instruct",
    "NVIDIA_KEY_QWEN":         "qwen/qwen2.5-coder-32b-instruct",
    "NVIDIA_KEY_KIMI":         "moonshotai/kimi-k2.6",
    "NVIDIA_KEY_MISTRAL":      "mistralai/mistral-medium-3-instruct",
    "NVIDIA_KEY_ZAIGLAM":      "zai-org/glam-5.1",
    "NVIDIA_KEY_DEEPSEEK_V4":  "deepseek-ai/deepseek-v4-flash",
    "NVIDIA_KEY_DEEPSEEK_PRO": "deepseek-ai/deepseek-v4-pro",
    "NVIDIA_KEY_MINIMAX":      "minimaxai/minimax-m2.7",
}


def show_key(label, val):
    if not val:
        print(f"  {R}✗{RS}  {label}: MISSING")
    elif len(val) < 10:
        print(f"  {R}✗{RS}  {label}: TOO SHORT ({len(val)} chars) — likely placeholder")
    else:
        preview = val[:12] + "..." + val[-4:]
        print(f"  {G}✓{RS}  {label}: {preview} ({len(val)} chars)")


def ok(label, text):
    print(f"  {G}✅  {label}{RS} — {text[:60]}")

def fail(label, err):
    print(f"  {R}❌  {label}{RS} — {str(err)[:120]}")

def skip(label, reason):
    print(f"  {Y}–   {label}{RS} — {reason}")


# ── SECTION 1: Key presence check ────────────────────────────────────────────

print(f"\n{B}{C}{'═'*60}{RS}")
print(f"{B}{C}   JARVIS COUNCIL — FULL DIAGNOSTIC{RS}")
print(f"{C}{'═'*60}{RS}\n")

print(f"{B}Section 1: Key presence{RS}")
show_key("AWS_BEARER_TOKEN_BEDROCK", BEDROCK_API_KEY)
show_key("AWS_ACCESS_KEY_ID",        AWS_ACCESS_KEY)
show_key("AWS_SECRET_ACCESS_KEY",    AWS_SECRET_KEY)
show_key("AWS_SESSION_TOKEN",        AWS_SESSION_TOKEN if len(AWS_SESSION_TOKEN) > 10 else "")
show_key("ANTHROPIC_API_KEY",        ANTHROPIC_KEY)
show_key("OPENROUTER_API_KEY",       OPENROUTER_KEY)
show_key("GOOGLE_API_KEY",           GOOGLE_KEY)
print()
for slot, val in NV_KEYS.items():
    show_key(slot, val)


# ── SECTION 2: Live API tests ─────────────────────────────────────────────────

async def test_all():
    print(f"\n{B}Section 2: Live API tests{RS}\n")

    async with httpx.AsyncClient() as client:

        # ── Anthropic ──────────────────────────────────────────────────────────
        print(f"{C}── Anthropic{RS}")
        if ANTHROPIC_KEY:
            try:
                r = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01",
                             "Content-Type": "application/json"},
                    json={"model": "claude-sonnet-4-6", "max_tokens": 8,
                          "messages": [{"role": "user", "content": "Reply with only: OK"}]},
                    timeout=30.0,
                )
                if r.status_code == 200:
                    ok("Claude Sonnet 4.6", r.json()["content"][0]["text"].strip())
                else:
                    fail("Claude Sonnet 4.6", f"HTTP {r.status_code}: {r.text[:200]}")
            except Exception as e:
                fail("Claude Sonnet 4.6", e)
        else:
            skip("Anthropic", "key not set")

        # ── OpenRouter ────────────────────────────────────────────────────────
        print(f"\n{C}── OpenRouter{RS}")
        if OPENROUTER_KEY:
            try:
                r = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENROUTER_KEY}",
                             "Content-Type": "application/json",
                             "HTTP-Referer": "https://aliyarsolutions.com"},
                    json={"model": "ai21/jamba-1-5-large",
                          "messages": [{"role": "user", "content": "Reply with only: OK"}],
                          "max_tokens": 8},
                    timeout=45.0,
                )
                if r.status_code == 200:
                    ok("AI21 Jamba Large", r.json()["choices"][0]["message"]["content"].strip())
                else:
                    fail("AI21 Jamba Large", f"HTTP {r.status_code}: {r.text[:200]}")
            except Exception as e:
                fail("AI21 Jamba Large", e)
        else:
            skip("OpenRouter", "key not set")

        # ── Google ────────────────────────────────────────────────────────────
        print(f"\n{C}── Google Gemini{RS}")
        if GOOGLE_KEY:
            try:
                r = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={GOOGLE_KEY}",
                    headers={"Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": "Reply with only: OK"}]}]},
                    timeout=45.0,
                )
                if r.status_code == 200:
                    ok("Gemini 2.5 Pro", r.json()["candidates"][0]["content"]["parts"][0]["text"].strip())
                else:
                    fail("Gemini 2.5 Pro", f"HTTP {r.status_code}: {r.text[:200]}")
            except Exception as e:
                fail("Gemini 2.5 Pro", e)
        else:
            skip("Google Gemini", "key not set — get from aistudio.google.com (starts with AIza)")

        # ── NVIDIA NIM ────────────────────────────────────────────────────────
        print(f"\n{C}── NVIDIA NIM (10 models){RS}")
        for slot, key in NV_KEYS.items():
            model = NVIDIA_MODELS[slot]
            name  = model.split("/")[-1]
            if not key:
                skip(name, "key not set")
                continue
            if not key.startswith("nvapi-"):
                fail(name, f"key is wrong format: starts with '{key[:8]}...' (must start with nvapi-)")
                continue
            try:
                r = await client.post(
                    "https://integrate.api.nvidia.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": model,
                          "messages": [{"role": "user", "content": "Reply with only: OK"}],
                          "max_tokens": 8, "temperature": 0.1},
                    timeout=30.0,
                )
                if r.status_code == 200:
                    ok(name, r.json()["choices"][0]["message"]["content"].strip())
                else:
                    fail(name, f"HTTP {r.status_code}: {r.text[:200]}")
            except Exception as e:
                fail(name, e)

    # ── AWS Bedrock ───────────────────────────────────────────────────────────
    print(f"\n{C}── AWS Bedrock (primary synthesizer){RS}")
    await test_bedrock()

    print(f"\n{C}{'═'*60}{RS}")
    print(f"{B}{Y}  Diagnostic complete. Fix any ❌ above.{RS}")
    print(f"{C}{'═'*60}{RS}\n")


def _bedrock_bearer_sync():
    try:
        import boto3
    except ImportError:
        install("boto3"); import boto3

    saved = {}
    for k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        saved[k] = os.environ.pop(k, None)
    os.environ["AWS_BEARER_TOKEN_BEDROCK"] = BEDROCK_API_KEY
    try:
        c = boto3.client("bedrock-runtime", region_name=AWS_REGION)
        MODELS = [
            "ap.anthropic.claude-opus-4-8-20250514-v1:0",
            "ap.anthropic.claude-sonnet-4-6-20251120-v1:0",
            "ap.anthropic.claude-3-5-sonnet-20241022-v2:0",
            "anthropic.claude-3-5-sonnet-20241022-v2:0",
        ]
        for mid in MODELS:
            try:
                resp = c.converse(
                    modelId=mid,
                    messages=[{"role": "user", "content": [{"text": "Reply with only: OK"}]}],
                    inferenceConfig={"maxTokens": 8},
                )
                text = "".join(
                    p.get("text", "")
                    for p in resp.get("output", {}).get("message", {}).get("content", [])
                )
                if text:
                    return True, f"{mid} → {text.strip()}"
            except Exception as e:
                last = str(e)[:150]
        return False, f"All models failed. Last: {last}"
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v


def _bedrock_iam_sync():
    try:
        import boto3
    except ImportError:
        install("boto3"); import boto3

    session_kwargs = {
        "aws_access_key_id":     AWS_ACCESS_KEY,
        "aws_secret_access_key": AWS_SECRET_KEY,
    }
    if AWS_SESSION_TOKEN and len(AWS_SESSION_TOKEN) > 50:
        session_kwargs["aws_session_token"] = AWS_SESSION_TOKEN

    c = boto3.Session(**session_kwargs).client("bedrock-runtime", region_name=AWS_REGION)
    MODELS = [
        "ap.anthropic.claude-opus-4-8-20250514-v1:0",
        "ap.anthropic.claude-sonnet-4-6-20251120-v1:0",
        "ap.anthropic.claude-3-5-sonnet-20241022-v2:0",
        "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "anthropic.claude-3-haiku-20240307-v1:0",
    ]
    last = ""
    for mid in MODELS:
        try:
            resp = c.converse(
                modelId=mid,
                messages=[{"role": "user", "content": [{"text": "Reply with only: OK"}]}],
                inferenceConfig={"maxTokens": 8},
            )
            text = "".join(
                p.get("text", "")
                for p in resp.get("output", {}).get("message", {}).get("content", [])
            )
            if text:
                return True, f"{mid} → {text.strip()}"
        except Exception as e:
            last = str(e)[:150]
    return False, f"All models failed. Last: {last}"


async def test_bedrock():
    if BEDROCK_API_KEY:
        print(f"  Testing Bedrock API Key (ABSK)...")
        try:
            success, msg = await asyncio.to_thread(_bedrock_bearer_sync)
            if success:
                ok("Bedrock API Key", msg)
            else:
                fail("Bedrock API Key", msg)
                print(f"       {Y}→ Go to AWS Console → Bedrock → Model Access → Enable Claude models for {AWS_REGION}{RS}")
        except Exception as e:
            fail("Bedrock API Key", e)
    else:
        skip("Bedrock API Key", "AWS_BEARER_TOKEN_BEDROCK not set")

    if AWS_ACCESS_KEY and AWS_SECRET_KEY:
        print(f"  Testing Bedrock IAM credentials...")
        try:
            success, msg = await asyncio.to_thread(_bedrock_iam_sync)
            if success:
                ok("Bedrock IAM", msg)
            else:
                fail("Bedrock IAM", msg)
                print(f"       {Y}→ Enable model access in AWS Console → Bedrock → Model Access{RS}")
        except Exception as e:
            fail("Bedrock IAM", e)
    else:
        skip("Bedrock IAM", "AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY not set")


asyncio.run(test_all())
