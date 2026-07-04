"""HQ-2: Execution Engine tool set.

Every tool here is sandboxed to the repo root and allowlisted — this is the
one place where model output turns into real file/shell/git actions, so it
is deliberately narrow. Anything not on the allowlist is refused, not
attempted. Destructive or infrastructure-level operations (deploy, terraform,
AWS) are NOT implemented as free-form shell here — they route through the
existing, already-reviewed GitHub Actions deploy pipeline instead, gated by
the Policy Engine tier for that operation.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[4]

# Command prefixes the Execution Engine is allowed to run. Anything else is
# refused unconditionally — this list is the actual safety boundary, not the
# model's judgment.
_ALLOWED_PREFIXES: list[tuple[str, ...]] = [
    ("git", "status"),
    ("git", "diff"),
    ("git", "log"),
    ("git", "show"),
    ("git", "add"),
    ("git", "commit"),
    ("git", "branch"),
    ("python3", "-m", "pytest"),
    ("npm", "test"),
    ("npm", "run", "build"),
    ("npm", "run", "lint"),
    ("docker", "compose", "ps"),
    ("docker", "compose", "logs"),
]

_DENYLIST_SUBSTRINGS = ["rm -rf", "sudo", "DROP TABLE", "--force", "shutdown", "> /dev", "curl ", "wget "]


def _resolve_in_repo(path: str) -> Path:
    """Resolve a path and refuse anything outside the repo root."""
    p = (REPO_ROOT / path).resolve()
    if REPO_ROOT not in p.parents and p != REPO_ROOT:
        raise PermissionError(f"Path '{path}' resolves outside the repository — refused.")
    return p


def read_file(path: str) -> dict[str, Any]:
    try:
        p = _resolve_in_repo(path)
        if not p.is_file():
            return {"ok": False, "error": f"Not a file: {path}"}
        return {"ok": True, "content": p.read_text(errors="replace")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def write_file(path: str, content: str) -> dict[str, Any]:
    try:
        p = _resolve_in_repo(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return {"ok": True, "path": str(p.relative_to(REPO_ROOT))}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def list_dir(path: str = ".") -> dict[str, Any]:
    try:
        p = _resolve_in_repo(path)
        if not p.is_dir():
            return {"ok": False, "error": f"Not a directory: {path}"}
        entries = sorted(e.name + ("/" if e.is_dir() else "") for e in p.iterdir())
        return {"ok": True, "entries": entries}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def run_command(argv: list[str], timeout: int = 120) -> dict[str, Any]:
    """Run an allowlisted command. `argv` must match one of the approved prefixes."""
    if not argv:
        return {"ok": False, "error": "Empty command"}

    joined = " ".join(argv)
    for bad in _DENYLIST_SUBSTRINGS:
        if bad.lower() in joined.lower():
            return {"ok": False, "error": f"Command contains a denied pattern: '{bad}'"}

    if not any(tuple(argv[: len(prefix)]) == prefix for prefix in _ALLOWED_PREFIXES):
        return {
            "ok": False,
            "error": (
                f"Command '{joined}' is not on the Execution Engine allowlist. "
                "Only git status/diff/log/show/add/commit/branch, pytest, npm test/build/lint, "
                "and docker compose ps/logs are permitted."
            ),
        }

    try:
        proc = subprocess.run(
            argv, cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-8000:],
            "stderr": proc.stderr[-4000:],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Command timed out after {timeout}s"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def git_current_commit() -> str | None:
    result = run_command(["git", "log", "-1", "--format=%H"])
    if result.get("ok"):
        return result["stdout"].strip()
    return None


def git_commit(message: str, paths: list[str]) -> dict[str, Any]:
    add_result = run_command(["git", "add", *paths])
    if not add_result.get("ok"):
        return add_result
    return run_command(["git", "commit", "-m", message])


def run_tests(path: str = "backend/tests") -> dict[str, Any]:
    return run_command(["python3", "-m", "pytest", path, "-q"])


# Tool registry — name → callable, with a JSON-schema-ish description for
# whichever model is proposing the plan (NIM/OpenRouter draft, Claude review).
TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "read_file": {"fn": read_file, "args": ["path"], "description": "Read a file's contents"},
    "write_file": {"fn": write_file, "args": ["path", "content"], "description": "Write/overwrite a file"},
    "list_dir": {"fn": list_dir, "args": ["path"], "description": "List a directory"},
    "run_command": {"fn": run_command, "args": ["argv"], "description": "Run an allowlisted command"},
    "git_commit": {"fn": git_commit, "args": ["message", "paths"], "description": "Stage and commit files"},
    "run_tests": {"fn": run_tests, "args": ["path"], "description": "Run the test suite for a path"},
}
