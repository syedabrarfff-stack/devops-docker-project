#!/usr/bin/env python3
"""
Post-deploy smoke test — verifies the deployed service is healthy and ready.
Used by the CI/CD pipeline immediately after each deployment.
Exits non-zero on failure (fails the GitHub Actions job).
"""

import os
import sys
import time
import urllib.request
import urllib.error

HEALTH_URL = os.environ.get("SARAH_HEALTH_URL", "http://localhost:8000/health")
MAX_RETRIES = 10
RETRY_DELAY_SECONDS = 5


def check(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def main():
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"Smoke test attempt {attempt}/{MAX_RETRIES}: {HEALTH_URL}")
        if check(HEALTH_URL):
            print("Health check passed.")
            sys.exit(0)
        time.sleep(RETRY_DELAY_SECONDS)

    print("Smoke test FAILED — service did not become healthy.")
    sys.exit(1)


if __name__ == "__main__":
    main()
