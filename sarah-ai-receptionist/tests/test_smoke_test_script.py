"""
scripts/smoke_test.py gates every production deploy -- a bug in it either
lets a broken deploy through (false pass) or blocks a healthy one forever
(false fail, as happened when the desiredCount-wait budget bug caused a
real but wrongly-diagnosed pipeline failure). It has no test coverage of
its own, so bugs in its retry/URL-derivation logic only ever surface live
in CI against real production traffic.

It's a standalone script (not a package under app/), so it's loaded here
by file path via importlib rather than a normal import.
"""

import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "smoke_test.py"


def _load_smoke_test_module():
    spec = importlib.util.spec_from_file_location("smoke_test", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def smoke_test(monkeypatch):
    # HEALTH_URL/API_URL are read from the environment at import time, so
    # each test needs a fresh module load after setting its own env vars.
    monkeypatch.setenv("SARAH_HEALTH_URL", "https://sarah.example.com/health")
    monkeypatch.delenv("SARAH_API_URL", raising=False)
    return _load_smoke_test_module()


def test_api_url_defaults_to_openapi_json_next_to_health_url(smoke_test):
    # The ALB only ever routes /health to voice-service by default -- API_URL
    # must land on a path the /api/*, /docs, /openapi.json listener rule
    # actually forwards to api-service, or this check silently tests nothing.
    assert smoke_test.API_URL == "https://sarah.example.com/openapi.json"


def test_api_url_respects_explicit_override(monkeypatch):
    monkeypatch.setenv("SARAH_HEALTH_URL", "https://sarah.example.com/health")
    monkeypatch.setenv("SARAH_API_URL", "https://sarah.example.com/api/custom-check")
    module = _load_smoke_test_module()
    assert module.API_URL == "https://sarah.example.com/api/custom-check"


def test_wait_until_healthy_returns_true_on_first_success(smoke_test):
    with patch.object(smoke_test, "check", return_value=True) as mock_check:
        assert smoke_test.wait_until_healthy("voice-service", "https://x/health") is True
        mock_check.assert_called_once()


def test_wait_until_healthy_retries_then_succeeds(smoke_test, monkeypatch):
    monkeypatch.setattr(smoke_test.time, "sleep", lambda _seconds: None)
    with patch.object(smoke_test, "check", side_effect=[False, False, True]) as mock_check:
        assert smoke_test.wait_until_healthy("api-service", "https://x/openapi.json") is True
        assert mock_check.call_count == 3


def test_wait_until_healthy_gives_up_after_max_retries(smoke_test, monkeypatch):
    monkeypatch.setattr(smoke_test.time, "sleep", lambda _seconds: None)
    with patch.object(smoke_test, "check", return_value=False) as mock_check:
        assert smoke_test.wait_until_healthy("worker-service", "https://x/never") is False
        assert mock_check.call_count == smoke_test.MAX_RETRIES


def test_main_exits_zero_when_both_services_healthy(smoke_test, monkeypatch):
    monkeypatch.setattr(smoke_test, "wait_until_healthy", lambda name, url: True)
    smoke_test.main()  # must not raise/exit


@pytest.mark.parametrize("voice_ok,api_ok", [(False, True), (True, False), (False, False)])
def test_main_exits_nonzero_if_either_service_unhealthy(smoke_test, monkeypatch, voice_ok, api_ok):
    results = {"voice-service": voice_ok, "api-service": api_ok}
    monkeypatch.setattr(smoke_test, "wait_until_healthy", lambda name, url: results[name])
    with pytest.raises(SystemExit) as exc_info:
        smoke_test.main()
    assert exc_info.value.code == 1
