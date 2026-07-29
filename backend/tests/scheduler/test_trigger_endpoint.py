"""Tests for POST /scheduler/jobs/{job_id}/trigger — Task #23 Phase A.

Before this fix, the route imported get_scheduler from the dead engine.py
module (a scheduler instance that never has any job registered on it, since
nothing ever starts it), so this endpoint always returned 404 regardless of
whether the job actually existed and was scheduled. It must now resolve
against the live scheduler in app.services.scheduler.scheduler.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.routes.auth import get_current_captain
from app.api.v1.routes.scheduler import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)  # router already declares prefix="/scheduler"
    app.dependency_overrides[get_current_captain] = lambda: {"role": "captain"}
    return TestClient(app)


class TestTriggerJobNow:
    def test_imports_get_scheduler_from_canonical_module_not_engine(self):
        import inspect
        from app.api.v1.routes import scheduler as route_module

        source = inspect.getsource(route_module.trigger_job_now)
        assert "app.services.scheduler.scheduler" in source
        assert "app.services.scheduler.engine" not in source

    def test_existing_job_triggers_successfully(self, client):
        fake_job = MagicMock()
        fake_scheduler = MagicMock()
        fake_scheduler.get_job.return_value = fake_job

        with patch("app.services.scheduler.scheduler.get_scheduler", return_value=fake_scheduler):
            resp = client.post("/scheduler/jobs/daily_lead_scoring/trigger")

        assert resp.status_code == 200
        body = resp.json()
        assert body["job_id"] == "daily_lead_scoring"
        assert body["status"] == "triggered"
        fake_scheduler.modify_job.assert_called_once()
        assert fake_scheduler.modify_job.call_args.args[0] == "daily_lead_scoring"

    def test_unknown_job_returns_404_not_silently_swallowed(self, client):
        fake_scheduler = MagicMock()
        fake_scheduler.get_job.return_value = None

        with patch("app.services.scheduler.scheduler.get_scheduler", return_value=fake_scheduler):
            resp = client.post("/scheduler/jobs/nonexistent_job/trigger")

        assert resp.status_code == 404
