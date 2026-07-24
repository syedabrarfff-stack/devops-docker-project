"""WhatsApp pairing got stuck: the Evolution instance hung in connectionState
"connecting" after a half-completed QR handshake, and WhatsApp's own app then
refused new device links ("Can't link new devices right now"). There was no
way to reset the instance from our backend — logout_instance/restart_instance
close that gap so a stuck handshake can be cleared before retrying.
"""
from unittest.mock import AsyncMock, patch

import pytest

from app.services.communication.whatsapp_transport import logout_instance, restart_instance


class TestInstanceReset:
    @pytest.mark.asyncio
    async def test_logout_instance_calls_evolution_delete_logout(self):
        with patch(
            "app.services.communication.whatsapp_transport.evolution_request",
            new_callable=AsyncMock,
            return_value={"ok": True, "status_code": 200, "data": {}},
        ) as mock_request:
            result = await logout_instance()

        mock_request.assert_awaited_once()
        method, path = mock_request.call_args.args
        assert method == "DELETE"
        assert path.startswith("/instance/logout/")
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_restart_instance_calls_evolution_put_restart(self):
        with patch(
            "app.services.communication.whatsapp_transport.evolution_request",
            new_callable=AsyncMock,
            return_value={"ok": True, "status_code": 200, "data": {}},
        ) as mock_request:
            result = await restart_instance()

        mock_request.assert_awaited_once()
        method, path = mock_request.call_args.args
        assert method == "PUT"
        assert path.startswith("/instance/restart/")
        assert result["ok"] is True
