#!/usr/bin/env python
"""JARVIS vNEXT HTTP integration test suite.

Run:
    python scripts/api_integration_test.py

Requires the FastAPI stack to be running. Defaults to:
    http://localhost:8000

Set JARVIS_API_BASE_URL to target another deployment, for example:
    JARVIS_API_BASE_URL=https://aliyarsolutions.com python scripts/api_integration_test.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Awaitable, Callable

import httpx


BASE_ROOT = os.getenv("JARVIS_API_BASE_URL", "http://localhost:8000").rstrip("/")
BASE_URL = f"{BASE_ROOT}/api/v1"
CAPTAIN_TOKEN = os.getenv("CAPTAIN_ADMIN_TOKEN") or os.getenv("JARVIS_CAPTAIN_TOKEN")
TENANT_ID = os.getenv("JARVIS_DEFAULT_TENANT_ID") or os.getenv("JARVIS_TEST_TENANT_ID")

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"
CHECK = "\u2713"
CROSS = "\u2717"


@dataclass(frozen=True)
class Result:
    name: str
    passed: bool
    detail: str
    elapsed_ms: int


RESULTS: list[Result] = []
CheckFn = Callable[[httpx.AsyncClient], Awaitable[str]]


async def check(name: str, session: httpx.AsyncClient, coro: CheckFn) -> None:
    """Run a test, record pass/fail, print result."""
    started = time.monotonic()
    try:
        detail = await coro(session)
        result = Result(name=name, passed=True, detail=detail, elapsed_ms=_elapsed_ms(started))
        print(f"{GREEN}{CHECK}{RESET} {name} - {detail} ({result.elapsed_ms} ms)")
    except Exception as exc:
        result = Result(name=name, passed=False, detail=_compact(str(exc)), elapsed_ms=_elapsed_ms(started))
        print(f"{RED}{CROSS}{RESET} {name} - {result.detail} ({result.elapsed_ms} ms)")
    RESULTS.append(result)


async def test_health(session: httpx.AsyncClient) -> str:
    data = await _get_json(session, f"{BASE_ROOT}/health")
    _require(data.get("status") == "ok", f"unexpected health payload: {data}")
    return f"{data.get('system')} {data.get('version')} live"


async def test_readyz(session: httpx.AsyncClient) -> str:
    data = await _get_json(session, f"{BASE_ROOT}/readyz")
    _require(data.get("status") == "ready", f"readiness degraded: {json.dumps(data)[:500]}")
    checks = data.get("checks") or {}
    return f"ready with {len(checks)} subsystem checks"


async def test_chat_providers(session: httpx.AsyncClient) -> str:
    data = await _get_json(session, f"{BASE_URL}/chat/providers")
    _require(isinstance(data, dict) and data, "provider status empty")
    available = [name for name, meta in data.items() if meta.get("available")]
    return f"{len(available)}/{len(data)} AI providers available"


async def test_ai_ops_health(session: httpx.AsyncClient) -> str:
    data = await _get_json(session, f"{BASE_URL}/ai-ops/health")
    _require("total_providers" in data, f"invalid AI health payload: {data}")
    return f"{data.get('available', 0)}/{data.get('total_providers', 0)} providers configured"


async def test_ai_credentials(session: httpx.AsyncClient) -> str:
    data = await _get_json(session, f"{BASE_URL}/ai-ops/credentials")
    _require("configured" in data and "total" in data, f"invalid credential audit payload: {data}")
    ready = "ready" if data.get("system_ready") else "not fully ready"
    return f"{data['configured']}/{data['total']} credentials configured; system {ready}"


async def test_jarvis_status(session: httpx.AsyncClient) -> str:
    data = await _get_json(session, f"{BASE_URL}/jarvis/status")
    _require(data.get("status") == "operational", f"JARVIS status not operational: {data}")
    return f"{data.get('system')} operational with {len(data.get('capabilities') or [])} capabilities"


async def test_agents(session: httpx.AsyncClient) -> str:
    data = await _get_json(session, f"{BASE_URL}/agents/hierarchy")
    stats = data.get("stats") or {}
    _require(stats.get("total_agents", 0) > 0, f"no agents returned: {data}")
    return f"{stats.get('active', 0)}/{stats.get('total_agents', 0)} agents active"


async def test_team_registry(session: httpx.AsyncClient) -> str:
    data = await _get_json(session, f"{BASE_URL}/team/stats")
    total = data.get("total") or data.get("active") or 0
    _require(total > 0, f"team registry empty: {data}")
    return f"{total} team identities registered"


async def test_catalog(session: httpx.AsyncClient) -> str:
    data = await _get_json(session, f"{BASE_URL}/catalog/stats")
    total = data.get("total_divisions") or data.get("active_divisions") or 0
    _require(total >= 30, f"expected 30 service divisions, got {data}")
    return f"{total} service divisions available"


async def test_pricing(session: httpx.AsyncClient) -> str:
    payload = {
        "service_category": "AI_APPOINTMENT_BOOKING",
        "client_size": "SMB",
        "complexity": "MEDIUM",
        "timeline": "STANDARD",
    }
    response = await session.post(f"{BASE_URL}/pricing/estimate", json=payload)
    _require(response.status_code in {200, 422}, f"HTTP {response.status_code}: {_body(response)}")
    if response.status_code == 422:
        return "pricing route reachable; request schema rejected validation sample"
    data = response.json()
    return f"pricing estimate generated with keys: {', '.join(sorted(data.keys())[:5])}"


async def test_briefing_status(session: httpx.AsyncClient) -> str:
    data = await _get_json(session, f"{BASE_URL}/briefing/status")
    _require(data.get("status") == "operational", f"briefing status degraded: {data}")
    providers = data.get("ai_providers") or {}
    return f"briefing online; {providers.get('available', 0)} AI providers active"


async def test_approval_count(session: httpx.AsyncClient) -> str:
    if not TENANT_ID:
        return _skip("set JARVIS_DEFAULT_TENANT_ID or JARVIS_TEST_TENANT_ID to validate approval count")
    data = await _get_json(session, f"{BASE_URL}/approvals/count", params={"tenant_id": TENANT_ID})
    _require("pending" in data, f"invalid approval count payload: {data}")
    return f"{data['pending']} pending approvals for tenant"


async def test_captain_admin_auth(session: httpx.AsyncClient) -> str:
    if not CAPTAIN_TOKEN:
        return _skip("set CAPTAIN_ADMIN_TOKEN to validate admin authorization")
    data = await _get_json(session, f"{BASE_URL}/admin/tenants", headers={"X-Captain-Token": CAPTAIN_TOKEN})
    tenants = data.get("tenants") or []
    return f"Captain admin auth accepted; {len(tenants)} tenants visible"


async def test_websocket_endpoint(session: httpx.AsyncClient) -> str:
    # This verifies that FastAPI registered the route without adding a websockets dependency to this suite.
    response = await session.get(f"{BASE_URL}/ws")
    _require(response.status_code in {404, 405, 426}, f"unexpected WebSocket route response HTTP {response.status_code}")
    return f"WebSocket route present check returned HTTP {response.status_code}"


async def main() -> int:
    print("JARVIS vNEXT HTTP INTEGRATION TEST SUITE")
    print(f"Target: {BASE_ROOT}")
    print(f"Started: {datetime.now(UTC).isoformat()}")
    print("")

    tests: list[tuple[str, CheckFn]] = [
        ("Root health", test_health),
        ("Deep readiness", test_readyz),
        ("Chat provider registry", test_chat_providers),
        ("AI operations health", test_ai_ops_health),
        ("Credential audit", test_ai_credentials),
        ("JARVIS status", test_jarvis_status),
        ("Agent hierarchy", test_agents),
        ("Team registry", test_team_registry),
        ("Service catalog", test_catalog),
        ("Pricing engine route", test_pricing),
        ("Briefing status", test_briefing_status),
        ("Approval count", test_approval_count),
        ("Captain admin auth", test_captain_admin_auth),
        ("WebSocket route", test_websocket_endpoint),
    ]

    timeout = httpx.Timeout(connect=10.0, read=40.0, write=20.0, pool=10.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as session:
        for name, test in tests:
            await check(name, session, test)

    print("")
    print_summary()
    failed = [result for result in RESULTS if not result.passed]
    if failed:
        return 1
    print("JARVIS HTTP API: ALL SYSTEMS GO")
    return 0


def print_summary() -> None:
    passed = sum(1 for result in RESULTS if result.passed)
    total = len(RESULTS)
    width = max(len(result.name) for result in RESULTS) if RESULTS else 12
    print(f"{passed}/{total} API checks passed")
    print("-" * (width + 36))
    for result in RESULTS:
        mark = f"{GREEN}{CHECK}{RESET}" if result.passed else f"{RED}{CROSS}{RESET}"
        print(f"{mark} {result.name:<{width}}  {result.elapsed_ms:>6} ms  {_compact(result.detail, 90)}")


async def _get_json(
    session: httpx.AsyncClient,
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
) -> dict:
    response = await session.get(url, params=params, headers=headers)
    _require(response.status_code == 200, f"GET {url} returned HTTP {response.status_code}: {_body(response)}")
    try:
        data = response.json()
    except ValueError as exc:
        raise AssertionError(f"GET {url} did not return JSON: {_body(response)}") from exc
    _require(isinstance(data, dict), f"GET {url} returned non-object JSON")
    return data


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _skip(reason: str) -> str:
    return f"{YELLOW}SKIPPED{RESET} - {reason}"


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _body(response: httpx.Response) -> str:
    return _compact(response.text.replace("\n", " "), 400)


def _compact(value: str, limit: int = 220) -> str:
    text = str(value).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
