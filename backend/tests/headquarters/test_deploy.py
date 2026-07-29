"""Tests for HQ-7: autonomous production deploy via SSM self-invoke."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.headquarters import deploy


class TestRunDeployValidation:
    @pytest.mark.asyncio
    async def test_unknown_action_rejected_without_touching_aws(self):
        with patch.object(deploy, "_ssm_client") as client_mock:
            result = await deploy.run_deploy("delete-everything")
            assert result["ok"] is False
            assert "Unknown deploy action" in result["error"]
            client_mock.assert_not_called()


class TestRunDeployTokenFailure:
    @pytest.mark.asyncio
    async def test_token_fetch_failure_returns_error_not_exception(self):
        with patch.object(deploy, "_ssm_client", return_value=MagicMock()):
            with patch.object(deploy, "_fetch_deploy_token", side_effect=RuntimeError("no parameter")):
                result = await deploy.run_deploy("git-pull-only")
                assert result["ok"] is False
                assert "Could not read deploy token" in result["error"]

    def test_placeholder_token_value_raises(self):
        client = MagicMock()
        client.get_parameter.return_value = {"Parameter": {"Value": "PENDING_SETUP_REPLACE_ME"}}
        with pytest.raises(RuntimeError, match="no real value set yet"):
            deploy._fetch_deploy_token(client)

    def test_real_token_value_returned(self):
        client = MagicMock()
        client.get_parameter.return_value = {"Parameter": {"Value": "ghp_realtoken123"}}
        assert deploy._fetch_deploy_token(client) == "ghp_realtoken123"


class TestRunDeployScriptFetchFailure:
    @pytest.mark.asyncio
    async def test_script_fetch_failure_returns_error(self):
        with (
            patch.object(deploy, "_ssm_client", return_value=MagicMock()),
            patch.object(deploy, "_fetch_deploy_token", return_value="tok"),
            patch.object(deploy, "_fetch_deploy_script", new=AsyncMock(side_effect=RuntimeError("404"))),
        ):
            result = await deploy.run_deploy("git-pull-only")
            assert result["ok"] is False
            assert "Could not fetch deploy script" in result["error"]


class TestSummarize:
    def test_success_status_with_marker_is_ok(self):
        result = deploy._summarize(
            "backend-only", "cmd-1",
            {"Status": "Success", "StandardOutputContent": "...BACKEND_HEALTHY\n", "StandardErrorContent": ""},
        )
        assert result["ok"] is True

    def test_build_failed_marker_overrides_success_status(self):
        result = deploy._summarize(
            "full-restart", "cmd-1",
            {"Status": "Success", "StandardOutputContent": "BUILD_FAILED\nsome error", "StandardErrorContent": ""},
        )
        assert result["ok"] is False

    def test_still_running_is_not_ok(self):
        result = deploy._summarize(
            "git-pull-only", "cmd-1",
            {"Status": "StillRunning", "StandardOutputContent": "", "StandardErrorContent": ""},
        )
        assert result["ok"] is False
        assert result["ssm_status"] == "StillRunning"

    def test_success_status_without_expected_marker_is_not_ok(self):
        result = deploy._summarize(
            "backend-only", "cmd-1",
            {"Status": "Success", "StandardOutputContent": "something unrelated", "StandardErrorContent": ""},
        )
        assert result["ok"] is False


class TestSendDeployCommand:
    def test_sends_to_correct_instance_and_document(self):
        client = MagicMock()
        client.send_command.return_value = {"Command": {"CommandId": "cmd-123"}}
        command_id = deploy._send_deploy_command(client, "c2NyaXB0", "backend-only")
        assert command_id == "cmd-123"
        _, kwargs = client.send_command.call_args
        assert kwargs["InstanceIds"] == [deploy.INSTANCE_ID]
        assert kwargs["DocumentName"] == "AWS-RunShellScript"
        assert "backend-only" in kwargs["Parameters"]["commands"][0]

    def test_command_fetches_token_on_host_not_embedded_in_payload(self):
        """The token must never appear in the SSM command text — AWS persists
        SendCommand parameters in queryable command history. The host should
        fetch its own copy via the AWS CLI at execution time instead."""
        client = MagicMock()
        client.send_command.return_value = {"Command": {"CommandId": "cmd-1"}}
        secret_token = "ghp_supersecrettoken"
        deploy._send_deploy_command(client, "c2NyaXB0", "git-pull-only")
        _, kwargs = client.send_command.call_args
        command_text = kwargs["Parameters"]["commands"][0]
        assert secret_token not in command_text
        assert "aws ssm get-parameter" in command_text
        assert deploy.DEPLOY_TOKEN_PARAMETER in command_text
