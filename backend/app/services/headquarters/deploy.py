"""HQ-7: Autonomous production deploy.

Headquarters runs inside the backend container, which deliberately has no
Docker socket or host repo mounted in — a backend compromise should not be
equivalent to host root. So deploys are triggered the same way the GitHub
Actions pipeline (.github/workflows/ec2-deploy.yml) already does it: via AWS
Systems Manager SendCommand against this instance, using the instance's own
role (jarvis-ops) instead of a GitHub Actions OIDC session.

The actual deploy logic is NOT duplicated here. It's fetched fresh from
GitHub on every run (scripts/ec2-deploy-script.sh, same file the Actions
workflow uses) so there is exactly one canonical deploy script — no second
copy to drift out of sync. The only thing read from AWS is a read-only
GitHub token (SSM Parameter Store, SecureString) used both to fetch that
script and to let it `git pull`.

Gated by the Policy Engine like every other Headquarters operation — see
authority_matrix.py's "production.deploy" rule (ASK_CAPTAIN by default).
"""
from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any

from app.core.config import settings

log = logging.getLogger(__name__)

INSTANCE_ID = "i-07887c05a28c22675"  # jarvis-work-dr-recovery — production since 2026-07-05 DR migration
DEPLOY_TOKEN_PARAMETER = "/jarvis/production/github-deploy-token"
DEPLOY_TOKEN_REGION = settings.AWS_REGION
DEPLOY_SCRIPT_URL = (
    "https://raw.githubusercontent.com/syedabrarfff-stack/devops-docker-project/"
    "claude/jarvis-cans-api-integration-ZThTD/scripts/ec2-deploy-script.sh"
)
ALLOWED_ACTIONS = {
    "git-pull-only",
    "verify-status",
    "nginx-reload",
    "backend-only",
    "frontend-only",
    "full-restart",
}
_SUCCESS_MARKERS = {
    "git-pull-only": "GIT PULL COMPLETE",
    "verify-status": "BACKEND OK",
    "nginx-reload": "HEALTH_OK",
    "backend-only": "BACKEND_HEALTHY",
    "frontend-only": "NGINX_PROXY_OK",
    "full-restart": "BACKEND_HEALTH_OK",
}
_FAILURE_MARKERS = ("BUILD_FAILED", "MIGRATION FAILED")


def _ssm_client():
    import boto3
    return boto3.client("ssm", region_name=settings.AWS_REGION)


async def run_deploy(action: str) -> dict[str, Any]:
    """Deploy `action` to the production instance. Returns a structured
    report — never raises for expected failure modes (bad token, build
    failure, timeout); those come back as {"ok": False, ...} for the
    orchestrator to narrate.
    """
    if action not in ALLOWED_ACTIONS:
        return {"ok": False, "error": f"Unknown deploy action: {action}. Allowed: {sorted(ALLOWED_ACTIONS)}"}

    client = _ssm_client()

    try:
        token = await asyncio.to_thread(_fetch_deploy_token, client)
    except Exception as exc:
        return {"ok": False, "error": f"Could not read deploy token from Parameter Store: {exc}"}

    try:
        script = await _fetch_deploy_script(token)
    except Exception as exc:
        return {"ok": False, "error": f"Could not fetch deploy script from GitHub: {exc}"}

    # The token is deliberately NOT embedded into the script here — AWS
    # persists SSM SendCommand parameters in queryable command history, which
    # would leave a live credential sitting in that history on every deploy.
    # Instead the raw (unsubstituted) script goes out, and the host fetches
    # its own copy of the token at execution time via the AWS CLI — it
    # already has ssm:GetParameter on this exact parameter (jarvis-ops role) —
    # so the token itself never appears in the command sent to SSM.
    script_b64 = base64.b64encode(script.encode()).decode()

    try:
        command_id = await asyncio.to_thread(
            _send_deploy_command, client, script_b64, action
        )
    except Exception as exc:
        return {"ok": False, "error": f"SSM send_command failed: {exc}"}

    result = await asyncio.to_thread(_poll_command, client, command_id)
    return _summarize(action, command_id, result)


def _fetch_deploy_token(client) -> str:
    resp = client.get_parameter(Name=DEPLOY_TOKEN_PARAMETER, WithDecryption=True)
    value = resp["Parameter"]["Value"]
    if not value or value == "PENDING_SETUP_REPLACE_ME":
        raise RuntimeError("Deploy token parameter exists but has no real value set yet")
    return value


async def _fetch_deploy_script(token: str) -> str:
    import httpx
    async with httpx.AsyncClient(timeout=15) as http:
        resp = await http.get(DEPLOY_SCRIPT_URL, headers={"Authorization": f"token {token}"})
        resp.raise_for_status()
        return resp.text


def _send_deploy_command(client, script_b64: str, action: str) -> str:
    # Fetch the token locally on the host (jarvis-ops role already has
    # ssm:GetParameter on this one parameter) and substitute it into the
    # script in-place — the token itself never transits the SSM command
    # definition, only this fetch-and-substitute wrapper does.
    wrapper = (
        "GH_TOKEN=$(aws ssm get-parameter --region " + f"{DEPLOY_TOKEN_REGION} "
        f"--name '{DEPLOY_TOKEN_PARAMETER}' --with-decryption "
        "--query Parameter.Value --output text) && "
        f"echo {script_b64} | base64 -d | sed \"s|__GHTOKEN__|$GH_TOKEN|g\" "
        f"| bash -s '{action}'"
    )
    resp = client.send_command(
        InstanceIds=[INSTANCE_ID],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [wrapper]},
        TimeoutSeconds=1800,
        Comment=f"Headquarters deploy: {action}",
    )
    return resp["Command"]["CommandId"]


def _poll_command(client, command_id: str, max_wait_s: int = 780, interval_s: int = 20) -> dict[str, Any]:
    import time as _time
    waited = 0
    while waited < max_wait_s:
        _time.sleep(interval_s)
        waited += interval_s
        try:
            result = client.get_command_invocation(CommandId=command_id, InstanceId=INSTANCE_ID)
        except client.exceptions.InvocationDoesNotExist:
            continue
        if result["Status"] in ("Success", "Failed", "Cancelled", "TimedOut"):
            return result
    return {"Status": "StillRunning", "StandardOutputContent": "", "StandardErrorContent": ""}


def _summarize(action: str, command_id: str, result: dict[str, Any]) -> dict[str, Any]:
    status = result.get("Status", "Unknown")
    output = result.get("StandardOutputContent", "")
    stderr = result.get("StandardErrorContent", "")
    success_marker = _SUCCESS_MARKERS.get(action, "")

    if any(marker in output for marker in _FAILURE_MARKERS):
        ok = False
    else:
        ok = status == "Success" and success_marker in output

    return {
        "ok": ok,
        "action": action,
        "command_id": command_id,
        "ssm_status": status,
        "output_tail": output[-3000:],
        "stderr_tail": stderr[-1500:] if stderr else "",
    }
