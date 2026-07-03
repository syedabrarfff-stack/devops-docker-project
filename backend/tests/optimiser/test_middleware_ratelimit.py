"""O5-5: Tests for IPRateLimitMiddleware."""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware import (
    IPRateLimitMiddleware,
    _IP_GLOBAL_LIMIT,
    _IP_SENSITIVE_LIMIT,
    _IP_WINDOW_SECS,
    _SENSITIVE_PREFIXES,
    _client_ip,
    _is_sensitive,
    _ip_windows,
    _sliding_window_check,
)


# ── Helper: clear rate limit state between tests ───────────────────────────────

@pytest.fixture(autouse=True)
def clear_ip_windows():
    """Reset the in-process rate limit windows before each test."""
    _ip_windows.clear()
    yield
    _ip_windows.clear()


# ── Constant checks ───────────────────────────────────────────────────────────

def test_global_limit():
    assert _IP_GLOBAL_LIMIT == 300


def test_sensitive_limit():
    assert _IP_SENSITIVE_LIMIT == 20


def test_window_secs():
    assert _IP_WINDOW_SECS == 60


# ── _sliding_window_check ─────────────────────────────────────────────────────

def test_sliding_window_allows_up_to_limit():
    now = time.monotonic()
    for i in range(10):
        assert _sliding_window_check("test_key", 10, now + i * 0.001) is True


def test_sliding_window_blocks_at_limit():
    now = time.monotonic()
    for _ in range(5):
        _sliding_window_check("key2", 5, now)
    assert _sliding_window_check("key2", 5, now) is False


def test_sliding_window_allows_after_expiry():
    now = 1000.0   # fake monotonic time
    # Fill the window.
    for _ in range(5):
        _sliding_window_check("key3", 5, now)
    # All 5 slots taken — next blocked.
    assert _sliding_window_check("key3", 5, now + 1) is False
    # Advance time past the window (61s); old entries expire.
    assert _sliding_window_check("key3", 5, now + _IP_WINDOW_SECS + 1) is True


# ── _client_ip ────────────────────────────────────────────────────────────────

def test_client_ip_from_forwarded_header():
    req = MagicMock()
    req.headers = {"X-Forwarded-For": "1.2.3.4, 10.0.0.1"}
    req.client = None
    assert _client_ip(req) == "1.2.3.4"


def test_client_ip_from_client_host():
    req = MagicMock()
    req.headers = {}
    req.client = MagicMock()
    req.client.host = "5.6.7.8"
    assert _client_ip(req) == "5.6.7.8"


def test_client_ip_unknown_when_no_client():
    req = MagicMock()
    req.headers = {}
    req.client = None
    assert _client_ip(req) == "unknown"


# ── _is_sensitive ─────────────────────────────────────────────────────────────

def test_sensitive_prefix_paths_are_sensitive():
    for prefix in _SENSITIVE_PREFIXES:
        req = MagicMock()
        req.url.path = f"{prefix}/something"
        req.method = "GET"
        assert _is_sensitive(req) is True, f"Expected {prefix} to be sensitive"


def test_api_mutation_methods_are_sensitive():
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        req = MagicMock()
        req.url.path = "/api/v1/leads"
        req.method = method
        assert _is_sensitive(req) is True


def test_api_get_on_non_sensitive_path_not_sensitive():
    req = MagicMock()
    req.url.path = "/api/v1/leads"
    req.method = "GET"
    assert _is_sensitive(req) is False


# ── FastAPI integration ───────────────────────────────────────────────────────

def _make_app():
    app = FastAPI()
    app.add_middleware(IPRateLimitMiddleware)

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.get("/api/v1/leads")
    async def leads():
        return {"leads": []}

    @app.post("/api/v1/captain/leads")
    async def create():
        return {"created": True}

    return app


def test_health_endpoint_exempt_from_rate_limit():
    """Health endpoint must never be rate-limited (would break load balancer checks)."""
    client = TestClient(_make_app(), raise_server_exceptions=False)
    for _ in range(5):
        response = client.get("/health")
        assert response.status_code == 200


def test_normal_request_passes():
    client = TestClient(_make_app(), raise_server_exceptions=False)
    response = client.get("/api/v1/leads")
    assert response.status_code == 200


def test_sensitive_path_rate_limited_after_limit(monkeypatch):
    """Exceed sensitive limit → 429 on the sensitive path."""
    monkeypatch.setattr("app.middleware._IP_SENSITIVE_LIMIT", 2)
    client = TestClient(_make_app(), raise_server_exceptions=False)

    # Two requests succeed.
    client.post("/api/v1/captain/leads")
    client.post("/api/v1/captain/leads")

    # Third should be rate-limited.
    response = client.post("/api/v1/captain/leads")
    assert response.status_code == 429
    assert "retry_after" in response.json()
    assert response.headers.get("Retry-After") is not None
