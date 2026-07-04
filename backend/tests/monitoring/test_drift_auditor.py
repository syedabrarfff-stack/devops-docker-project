"""Tests for the permanent Drift Auditor — the architectural rule that
continuously checks the repo/infra for duplicate config and stale files.
"""
from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.services.monitoring import drift_auditor


@pytest.fixture
def fake_repo(tmp_path, monkeypatch):
    (tmp_path / "infrastructure").mkdir()
    (tmp_path / "infrastructure" / "docker-compose.yml").write_text("services: {}\n")
    (tmp_path / "backend" / "alembic" / "versions").mkdir(parents=True)
    monkeypatch.setattr(drift_auditor, "REPO_ROOT", tmp_path)
    return tmp_path


class TestDuplicateComposeFiles:
    @pytest.mark.asyncio
    async def test_single_compose_file_is_clean(self, fake_repo):
        report = await drift_auditor.run_drift_audit()
        assert not any("docker-compose" in a for a in report["alerts"])

    @pytest.mark.asyncio
    async def test_duplicate_compose_files_flagged(self, fake_repo):
        (fake_repo / "infrastructure" / "docker-compose.prod.yml").write_text("services: {}\n")
        report = await drift_auditor.run_drift_audit()
        assert any("Multiple docker-compose files" in a for a in report["alerts"])


class TestStrayEnvFiles:
    @pytest.mark.asyncio
    async def test_no_stray_env_is_clean(self, fake_repo):
        report = await drift_auditor.run_drift_audit()
        assert not any(".env" in a for a in report["alerts"])

    @pytest.mark.asyncio
    async def test_backend_env_flagged_not_deleted(self, fake_repo):
        backend_dir = fake_repo / "backend"
        backend_dir.mkdir(exist_ok=True)
        stray = backend_dir / ".env"
        stray.write_text("POSTGRES_PASSWORD=different_from_root\n")

        report = await drift_auditor.run_drift_audit()

        assert any("backend/.env" in a for a in report["alerts"])
        assert stray.exists(), "stray .env must be reported, never auto-deleted"


class TestDuplicateMigrationRevisions:
    @pytest.mark.asyncio
    async def test_unique_revisions_clean(self, fake_repo):
        versions = fake_repo / "backend" / "alembic" / "versions"
        (versions / "0001_a.py").write_text('revision = "0001_a"\n')
        (versions / "0002_b.py").write_text('revision = "0002_b"\n')
        report = await drift_auditor.run_drift_audit()
        assert not any("revision" in a for a in report["alerts"])

    @pytest.mark.asyncio
    async def test_duplicate_revision_id_flagged(self, fake_repo):
        versions = fake_repo / "backend" / "alembic" / "versions"
        (versions / "0001_a.py").write_text('revision = "clash"\n')
        (versions / "0002_b.py").write_text('revision = "clash"\n')
        report = await drift_auditor.run_drift_audit()
        assert any("clash" in a for a in report["alerts"])


class TestBackupPruning:
    @pytest.mark.asyncio
    async def test_recent_backup_not_pruned(self, fake_repo):
        recent_stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        recent = fake_repo / f"nginx.conf.bak-{recent_stamp}"
        recent.write_text("x")
        report = await drift_auditor.run_drift_audit()
        assert recent.exists()
        assert not any("pruned_stale_backups" in a for a in report["actions"])

    @pytest.mark.asyncio
    async def test_old_backup_is_pruned(self, fake_repo):
        old_stamp = (datetime.now(UTC) - timedelta(days=45)).strftime("%Y%m%d%H%M%S")
        old = fake_repo / f".env.bak-{old_stamp}"
        old.write_text("x")
        report = await drift_auditor.run_drift_audit()
        assert not old.exists()
        assert any("pruned_stale_backups:1" in a for a in report["actions"])

    @pytest.mark.asyncio
    async def test_malformed_backup_suffix_ignored(self, fake_repo):
        bad = fake_repo / ".env.bak-not-a-timestamp"
        bad.write_text("x")
        report = await drift_auditor.run_drift_audit()
        assert bad.exists()


class TestCleanRepoProducesNoNoise:
    @pytest.mark.asyncio
    async def test_clean_repo_reports_nothing(self, fake_repo):
        report = await drift_auditor.run_drift_audit()
        assert report["actions"] == []
        assert report["alerts"] == []
        assert "duration_ms" in report
