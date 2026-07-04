"""JARVIS Drift Auditor — the permanent architectural rule Captain asked for:
continuously check the repository and running infrastructure for duplicate
configuration, stale files, and conflicting definitions that could cause the
same class of outage as the 2026-07-04 incident (a stale docker-compose.prod.yml
and a shadow .env with different credentials).

Policy, deliberately conservative:
  - Only ONE class of finding is auto-fixed: our own timestamped backup files
    (.bak-YYYYMMDDHHMMSS) older than the retention window — unambiguously safe,
    self-created, provably stale.
  - Everything else (duplicate compose files, stray .env files, duplicate
    Alembic revision IDs) is reported, never auto-deleted — deciding whether a
    duplicate file is "obviously stale" or "someone's in-progress work"
    requires judgment this auditor doesn't have. Report it into Headquarters
    chat via the same channel as the self-healer; a human (or a future
    Mission-Planner-routed task) decides the fix.
"""
from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[4]
BACKUP_RETENTION_DAYS = 30
_BACKUP_SUFFIX_RE = re.compile(r"\.bak-(\d{14})$")


async def run_drift_audit() -> dict:
    """Full drift-audit pass. Returns a report dict for observability, same
    shape as self_healer's report so it can share the same reporting path.
    """
    started = datetime.now(UTC)
    report: dict = {"started_at": started.isoformat(), "actions": [], "alerts": []}

    _check_duplicate_compose_files(report)
    _check_stray_env_files(report)
    _check_duplicate_migration_revisions(report)
    _prune_stale_backups(report)

    report["duration_ms"] = int((datetime.now(UTC) - started).total_seconds() * 1000)
    logger.info(
        "Drift audit complete: %d action(s), %d alert(s)",
        len(report["actions"]), len(report["alerts"]),
    )
    return report


def _check_duplicate_compose_files(report: dict) -> None:
    """Exactly one docker-compose*.yml should exist under infrastructure/."""
    infra_dir = REPO_ROOT / "infrastructure"
    if not infra_dir.is_dir():
        return
    compose_files = sorted(p.name for p in infra_dir.glob("docker-compose*.yml"))
    if len(compose_files) > 1:
        report["alerts"].append(
            f"Multiple docker-compose files in infrastructure/: {compose_files} — "
            "only one should exist; the rest risk silent config drift like the "
            "2026-07-04 incident. Needs a human decision on which to keep."
        )


def _check_stray_env_files(report: dict) -> None:
    """.env files outside the canonical root location can silently shadow it —
    pydantic-settings checks the current working directory first.
    """
    suspect_paths = [
        REPO_ROOT / "backend" / ".env",
        REPO_ROOT / "frontend" / ".env",
    ]
    found = [str(p.relative_to(REPO_ROOT)) for p in suspect_paths if p.is_file()]
    if found:
        report["alerts"].append(
            f"Found .env file(s) outside the canonical root location: {found} — "
            "these can silently override the real configuration depending on "
            "which directory the app is started from. Needs review, not auto-deleted."
        )


def _check_duplicate_migration_revisions(report: dict) -> None:
    """Two Alembic migrations sharing a revision id breaks the migration chain —
    can't be auto-fixed (needs a human to pick which one gets renumbered).
    """
    versions_dir = REPO_ROOT / "backend" / "alembic" / "versions"
    if not versions_dir.is_dir():
        return
    seen: dict[str, str] = {}
    dupes: set[str] = set()
    for f in versions_dir.glob("*.py"):
        text = f.read_text(errors="ignore")
        m = re.search(r'^revision\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
        if not m:
            continue
        rev = m.group(1)
        if rev in seen and seen[rev] != f.name:
            dupes.add(rev)
        else:
            seen[rev] = f.name
    if dupes:
        report["alerts"].append(f"Duplicate Alembic revision id(s) detected: {sorted(dupes)}")


def _prune_stale_backups(report: dict) -> None:
    """The only auto-fix: delete our own timestamped .bak files past retention.
    Safe because the timestamp in the filename proves age and origin.
    """
    cutoff = datetime.now(UTC) - timedelta(days=BACKUP_RETENTION_DAYS)
    pruned = 0
    for p in REPO_ROOT.rglob("*.bak-*"):
        if ".git" in p.parts:
            continue
        m = _BACKUP_SUFFIX_RE.search(p.name)
        if not m:
            continue
        try:
            stamp = datetime.strptime(m.group(1), "%Y%m%d%H%M%S").replace(tzinfo=UTC)
        except ValueError:
            continue
        if stamp < cutoff:
            try:
                p.unlink()
                pruned += 1
            except OSError as exc:
                logger.warning("Drift auditor: could not prune %s: %s", p, exc)
    if pruned:
        report["actions"].append(f"pruned_stale_backups:{pruned}")
