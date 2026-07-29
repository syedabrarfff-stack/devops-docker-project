"""Tests for HQ-2: Execution Engine tool set — sandboxing, allowlist, denylist."""
from __future__ import annotations

from app.services.headquarters import tools


class TestPathSandboxing:
    def test_reads_file_inside_repo(self):
        result = tools.read_file("README.md")
        assert result["ok"] is True
        assert isinstance(result["content"], str)

    def test_rejects_path_traversal_outside_repo(self):
        result = tools.read_file("../../../../../etc/passwd")
        assert result["ok"] is False

    def test_rejects_absolute_path_outside_repo(self):
        result = tools.read_file("/etc/passwd")
        assert result["ok"] is False

    def test_write_then_read_roundtrip(self, tmp_path_factory=None):
        write_result = tools.write_file("tests/headquarters/_scratch.txt", "hello hq")
        assert write_result["ok"] is True
        read_result = tools.read_file("tests/headquarters/_scratch.txt")
        assert read_result["ok"] is True
        assert read_result["content"] == "hello hq"
        # cleanup
        (tools.REPO_ROOT / "tests/headquarters/_scratch.txt").unlink(missing_ok=True)


class TestListDir:
    def test_lists_repo_root(self):
        result = tools.list_dir(".")
        assert result["ok"] is True
        assert "backend" in result["entries"] or "backend/" in result["entries"]

    def test_nonexistent_dir_returns_error(self):
        result = tools.list_dir("this_directory_does_not_exist_xyz")
        assert result["ok"] is False


class TestRunCommandAllowlist:
    def test_allowed_git_status_runs(self):
        result = tools.run_command(["git", "status"])
        assert "ok" in result

    def test_disallowed_command_refused(self):
        result = tools.run_command(["ls", "-la"])
        assert result["ok"] is False
        assert "not on the Execution Engine allowlist" in result["error"]

    def test_curl_refused_via_denylist(self):
        result = tools.run_command(["curl", "https://example.com"])
        assert result["ok"] is False

    def test_denylisted_pattern_refused_even_if_prefix_matches(self):
        result = tools.run_command(["git", "commit", "--force", "-m", "x"])
        assert result["ok"] is False
        assert "denied pattern" in result["error"]

    def test_rm_rf_refused(self):
        result = tools.run_command(["rm", "-rf", "/"])
        assert result["ok"] is False

    def test_sudo_refused(self):
        result = tools.run_command(["sudo", "reboot"])
        assert result["ok"] is False

    def test_empty_command_refused(self):
        result = tools.run_command([])
        assert result["ok"] is False


class TestToolRegistry:
    def test_registry_has_expected_tools(self):
        assert "read_file" in tools.TOOL_REGISTRY
        assert "write_file" in tools.TOOL_REGISTRY
        assert "run_command" in tools.TOOL_REGISTRY
        assert "git_commit" in tools.TOOL_REGISTRY
        assert "run_tests" in tools.TOOL_REGISTRY

    def test_registry_entries_are_callable(self):
        for name, entry in tools.TOOL_REGISTRY.items():
            assert callable(entry["fn"]), f"{name} is not callable"
