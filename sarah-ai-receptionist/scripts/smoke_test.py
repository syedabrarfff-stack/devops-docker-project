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
# /health is served by every backend container, but the ALB's default listener
# action always routes it to the voice-service target group -- it never
# touches api-service. Only paths matching the /api/*, /docs, /openapi.json
# listener rule land on api-service. Checking /health alone meant a broken
# api-service (bad task def, crash loop, wrong image) could sit behind a
# "successful" deploy indefinitely, since nothing in the smoke test ever
# routed a request to it. /openapi.json is served by the same FastAPI app and
# matches that listener rule, so it's a cheap way to prove api-service is
# actually reachable and responding, not just that voice-service is.
API_URL = os.environ.get("SARAH_API_URL", HEALTH_URL.rsplit("/", 1)[0] + "/openapi.json")
MAX_RETRIES = 10
RETRY_DELAY_SECONDS = 5


def check(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def wait_until_healthy(name: str, url: str) -> bool:
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"Smoke test attempt {attempt}/{MAX_RETRIES} [{name}]: {url}")
        if check(url):
            print(f"{name} check passed.")
            return True
        time.sleep(RETRY_DELAY_SECONDS)
    print(f"Smoke test FAILED — {name} did not become healthy: {url}")
    return False


def main():
    voice_ok = wait_until_healthy("voice-service", HEALTH_URL)
    api_ok = wait_until_healthy("api-service", API_URL)

    if not (voice_ok and api_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
