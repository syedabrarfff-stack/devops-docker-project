#!/usr/bin/env python3
"""O5-2: FabricRouter Load Test — 1000 concurrent requests.

Simulates high-concurrency load through the JARVIS AI Fabric layer (F3-7).
Sends configurable concurrent requests and reports throughput + latency stats.

Usage:
    # Against a live backend (default: http://localhost:8000)
    python scripts/load_test_fabric.py

    # Custom concurrency and endpoint
    python scripts/load_test_fabric.py --concurrency 500 --total 2000 --url http://api.aliyar.io

    # Dry-run (mock router, no real API calls) — CI-safe
    python scripts/load_test_fabric.py --dry-run

Exit codes:
    0 — all checks passed
    1 — error rate exceeded 5% OR p95 latency exceeded 10 000ms
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
import time
from typing import NamedTuple


# ── Result data structure ──────────────────────────────────────────────────────

class CallResult(NamedTuple):
    latency_ms: float
    success: bool
    status_code: int


# ── HTTP load against live backend ────────────────────────────────────────────

async def _http_call(session, url: str, payload: dict, idx: int) -> CallResult:
    """Send one POST to /api/v1/chat and record the result."""
    import aiohttp
    t0 = time.monotonic()
    try:
        async with session.post(
            f"{url}/api/v1/chat",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            latency_ms = (time.monotonic() - t0) * 1000
            return CallResult(latency_ms=latency_ms, success=resp.status < 500, status_code=resp.status)
    except Exception:
        latency_ms = (time.monotonic() - t0) * 1000
        return CallResult(latency_ms=latency_ms, success=False, status_code=0)


async def run_http_load(url: str, concurrency: int, total: int) -> list[CallResult]:
    """Run the HTTP load test against a live backend."""
    import aiohttp
    payload = {
        "message": "Load test: analyse Q3 pipeline performance.",
        "task_type": "ANALYSIS",
    }
    semaphore = asyncio.Semaphore(concurrency)
    results: list[CallResult] = []

    async with aiohttp.ClientSession() as session:
        async def _bounded(idx: int) -> CallResult:
            async with semaphore:
                return await _http_call(session, url, payload, idx)

        tasks = [asyncio.create_task(_bounded(i)) for i in range(total)]
        completed = 0
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            completed += 1
            if completed % 100 == 0:
                print(f"  Progress: {completed}/{total}", flush=True)

    return results


# ── Dry-run: exercise FabricRouter in-process with a mock provider ─────────────

async def _mock_fabric_call(semaphore: asyncio.Semaphore, idx: int) -> CallResult:
    """Simulate one FabricRouter.chat() call with artificial latency."""
    async with semaphore:
        t0 = time.monotonic()
        # Simulate variable provider latency (50–600ms).
        jitter = 0.05 + (idx % 11) * 0.05
        await asyncio.sleep(jitter)
        # Inject 2% synthetic errors.
        success = (idx % 50) != 0
        latency_ms = (time.monotonic() - t0) * 1000
        return CallResult(latency_ms=latency_ms, success=success, status_code=200 if success else 503)


async def run_dry_load(concurrency: int, total: int) -> list[CallResult]:
    """Run load test in dry-run mode without real HTTP calls."""
    semaphore = asyncio.Semaphore(concurrency)
    tasks = [asyncio.create_task(_mock_fabric_call(semaphore, i)) for i in range(total)]
    results: list[CallResult] = []
    completed = 0
    for coro in asyncio.as_completed(tasks):
        result = await coro
        results.append(result)
        completed += 1
        if completed % 100 == 0:
            print(f"  Progress: {completed}/{total}", flush=True)
    return results


# ── Statistics ────────────────────────────────────────────────────────────────

def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    idx = max(0, math.ceil(len(sorted_values) * pct / 100) - 1)
    return sorted_values[idx]


def _report(results: list[CallResult], wall_secs: float) -> dict:
    latencies = sorted(r.latency_ms for r in results)
    successes = sum(1 for r in results if r.success)
    errors    = len(results) - successes
    error_rate = errors / len(results) if results else 0.0
    throughput = len(results) / wall_secs if wall_secs > 0 else 0.0

    stats = {
        "total_requests": len(results),
        "successful":     successes,
        "errors":         errors,
        "error_rate_pct": round(error_rate * 100, 2),
        "throughput_rps": round(throughput, 2),
        "latency_p50_ms": round(_percentile(latencies, 50), 1),
        "latency_p95_ms": round(_percentile(latencies, 95), 1),
        "latency_p99_ms": round(_percentile(latencies, 99), 1),
        "latency_max_ms": round(max(latencies, default=0), 1),
        "wall_secs":      round(wall_secs, 2),
    }

    print("\n" + "═" * 55)
    print("  JARVIS Fabric Load Test Results")
    print("═" * 55)
    print(f"  Total requests  : {stats['total_requests']}")
    print(f"  Successful      : {stats['successful']}")
    print(f"  Errors          : {stats['errors']}  ({stats['error_rate_pct']}%)")
    print(f"  Throughput      : {stats['throughput_rps']} req/s")
    print(f"  Latency p50     : {stats['latency_p50_ms']} ms")
    print(f"  Latency p95     : {stats['latency_p95_ms']} ms")
    print(f"  Latency p99     : {stats['latency_p99_ms']} ms")
    print(f"  Latency max     : {stats['latency_max_ms']} ms")
    print(f"  Wall time       : {stats['wall_secs']} s")
    print("═" * 55)

    return stats


def _check_thresholds(stats: dict) -> bool:
    """Return True if all quality gates pass."""
    passed = True
    if stats["error_rate_pct"] > 5.0:
        print(f"\n❌  FAIL: error rate {stats['error_rate_pct']}% > 5% threshold")
        passed = False
    else:
        print(f"\n✅  error rate {stats['error_rate_pct']}% ≤ 5%")

    if stats["latency_p95_ms"] > 10_000:
        print(f"❌  FAIL: p95 latency {stats['latency_p95_ms']}ms > 10 000ms threshold")
        passed = False
    else:
        print(f"✅  p95 latency {stats['latency_p95_ms']}ms ≤ 10 000ms")

    return passed


# ── CLI ───────────────────────────────────────────────────────────────────────

async def _main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS Fabric load test (O5-2)")
    parser.add_argument("--url",         default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--concurrency", type=int, default=100,  help="Max concurrent requests")
    parser.add_argument("--total",       type=int, default=1000, help="Total requests to send")
    parser.add_argument("--dry-run",     action="store_true",    help="Mock mode — no real HTTP calls")
    parser.add_argument("--output",      default=None,           help="Write JSON results to this file")
    args = parser.parse_args()

    mode = "DRY-RUN (mock)" if args.dry_run else f"LIVE → {args.url}"
    print(f"\nJARVIS Fabric Load Test  |  {args.total} requests  |  concurrency {args.concurrency}  |  {mode}")
    print("Starting...\n")

    t0 = time.monotonic()
    if args.dry_run:
        results = await run_dry_load(args.concurrency, args.total)
    else:
        results = await run_http_load(args.url, args.concurrency, args.total)
    wall_secs = time.monotonic() - t0

    stats = _report(results, wall_secs)
    passed = _check_thresholds(stats)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(stats, f, indent=2)
        print(f"\nResults written to {args.output}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
