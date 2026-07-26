#!/usr/bin/env python3
"""
Points a Twilio phone number's voice webhook at your running server.
Usage: python scripts/setup_twilio.py --url https://your-domain-or-ngrok-url --phone +1XXXXXXXXXX
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from twilio.rest import Client  # noqa: E402
from app.config.settings import get_settings  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Base URL of your running server (https://... or ngrok URL)")
    parser.add_argument("--phone", required=False, help="Twilio number to configure (defaults to TWILIO_PHONE_NUMBER)")
    args = parser.parse_args()

    settings = get_settings()
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

    phone = args.phone or settings.twilio_phone_number
    webhook_url = f"{args.url.rstrip('/')}/incoming-call"

    numbers = client.incoming_phone_numbers.list(phone_number=phone)
    if not numbers:
        print(f"No Twilio number found matching {phone}")
        return

    numbers[0].update(voice_url=webhook_url, voice_method="POST")
    print(f"Configured {phone} -> {webhook_url}")


if __name__ == "__main__":
    main()
