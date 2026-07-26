#!/usr/bin/env python3
"""
Simulates a phone call in the terminal — no Twilio number needed.
Type what a caller would say; Sarah responds using the real AI brain.

Usage: python scripts/test_call.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.ai_brain import AIBrain  # noqa: E402
from app.prompts.dental_receptionist import get_default_clinic_config  # noqa: E402


async def main():
    print("=" * 60)
    print("Sarah AI Receptionist — Terminal Test")
    print("Type what the caller would say. Ctrl+C to exit.")
    print("=" * 60)

    brain = AIBrain(get_default_clinic_config())

    greeting = f"Hi, thank you for calling {brain.clinic_config['name']}! This is Sarah, how can I help you today?"
    print(f"\nSarah: {greeting}")

    try:
        while True:
            caller_text = input("\nYou: ").strip()
            if not caller_text:
                continue

            print("Sarah: ", end="", flush=True)
            async for kind, payload in brain.stream_response(caller_text):
                if kind == "sentence":
                    print(payload, end=" ", flush=True)
                elif kind == "action" and payload:
                    print(f"\n  [action: {payload.action} {payload.params}]", end="")
            print()

    except (KeyboardInterrupt, EOFError):
        print("\n\nCall ended.")
    finally:
        await brain.close()


if __name__ == "__main__":
    asyncio.run(main())
