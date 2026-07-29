"""Regression coverage for a platform-wide bug found via live production audit:

`from __future__ import annotations` (PEP 563 postponed evaluation) combined
with slowapi's `@limiter.limit(...)` decorator breaks FastAPI's ability to
resolve a Pydantic-model body parameter's real type. FastAPI/Pydantic ends up
evaluating the string annotation against the *decorator's* module globals
(slowapi's), can't find the model class name there, and silently falls back
to treating the parameter as a required query parameter — so every POST
endpoint hitting this combination returned 422 "query.body: Field required"
no matter what was actually sent in the request body.

This affected 39 route modules — every rate-limited POST/PUT action across
the dashboard (Council convene/stream, outreach, proposals, revenue actions,
etc.) while GET-only pages kept working, which is exactly why it looked like
"the dashboard is a catalogue you can look at but nothing reacts to clicks."

Fix: remove `from __future__ import annotations` from the affected route
modules (verified none of them relied on postponed evaluation for forward
references). The test below (1) proves the specific failure mode is gone for
the endpoint the bug was first caught on, and (2) statically guards against
any route module ever reintroducing the dangerous combination.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROUTES_DIR = Path(__file__).resolve().parents[2] / "app" / "api" / "v1" / "routes"


def _uses_future_annotations(tree: ast.Module) -> bool:
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            if any(alias.name == "annotations" for alias in node.names):
                return True
    return False


def _uses_limiter_decorator(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                dec_str = ast.dump(dec)
                if "limiter" in dec_str and "limit" in dec_str:
                    return True
    return False


class TestNoFutureAnnotationsWithRateLimiter:
    """Static guard: this exact combination silently breaks body parsing.
    Never let both patterns land in the same route module again."""

    def test_no_route_module_combines_future_annotations_with_limiter(self):
        offenders = []
        for path in sorted(ROUTES_DIR.glob("*.py")):
            source = path.read_text()
            tree = ast.parse(source, filename=str(path))
            if _uses_future_annotations(tree) and _uses_limiter_decorator(tree):
                offenders.append(path.name)

        assert offenders == [], (
            "These route modules combine `from __future__ import annotations` with "
            "`@limiter.limit(...)`, which breaks FastAPI's Pydantic body-model "
            "resolution (see module docstring for the full mechanism): "
            f"{offenders}"
        )


class TestCouncilConveneBodyParsing:
    """Direct proof the specific bug the Captain hit is fixed."""

    def _client(self):
        from app.api.v1.routes import council
        from app.api.v1.routes.auth import get_current_captain

        app = FastAPI()
        app.include_router(council.router, prefix="/api/v1")
        app.dependency_overrides[get_current_captain] = lambda: {"sub": "captain", "role": "captain"}
        return TestClient(app)

    def test_convene_no_longer_422s_on_a_well_formed_body(self):
        client = self._client()
        resp = client.post(
            "/api/v1/council/convene",
            json={"question": "A well-formed test question.", "context": {}, "council_type": "rapid"},
        )
        # The old bug always returned 422 with a query.body "Field required" error
        # regardless of what was sent. Once body parsing works, the request reaches
        # real business logic and fails for a real reason instead (no tenant context
        # injected by this bare TestClient) — proving the body was actually parsed.
        assert resp.status_code != 422, (
            f"Body parsing regression: got 422 again — {resp.text}"
        )
        body = resp.json()
        assert "query.body" not in str(body)
