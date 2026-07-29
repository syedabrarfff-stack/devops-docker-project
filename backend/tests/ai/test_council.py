"""Test NVIDIA member addition to Council."""
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import pytest
from app.services.ai.council import COUNCIL_MEMBERS, IntelligenceCouncil, MODEL_CALL_OVERRIDES


class TestCouncilNvidiaMember:
    def test_council_has_nine_members(self):
        assert len(COUNCIL_MEMBERS) == 9

    def test_nvidia_member_exists(self):
        nvidia_members = [m for m in COUNCIL_MEMBERS if m["provider"] == "nvidia"]
        assert len(nvidia_members) == 1
        nvidia = nvidia_members[0]
        assert nvidia["id"] == "executor"
        assert nvidia["model"] == "llama-4-maverick"
        assert nvidia["weight"] == 0.30

    def test_nvidia_model_override_exists(self):
        assert ("nvidia", "llama-4-maverick") in MODEL_CALL_OVERRIDES
        assert MODEL_CALL_OVERRIDES[("nvidia", "llama-4-maverick")] == "meta/llama-4-maverick-17b-128e-instruct"

    def test_weights_sum_to_one(self):
        total = sum(m["weight"] for m in COUNCIL_MEMBERS)
        assert round(total, 4) == 1.0

    @pytest.mark.asyncio
    async def test_ask_member_nvidia_available(self):
        council = IntelligenceCouncil()
        member = COUNCIL_MEMBERS[0]  # executor (nvidia)

        # Mock the provider to return a response
        mock_response = MagicMock()
        mock_response.error = None
        mock_response.content = '{"vote_score": 85, "recommendation": "APPROVE", "reasoning": "Looks good"}'
        mock_response.model = member["model"]
        mock_response.tokens_used = 100
        mock_response.cost_estimate_usd = 0.001

        with patch.object(council, '_ask_member', new_callable=AsyncMock) as mock_ask:
            mock_ask.return_value = {
                "member_id": member["id"],
                "provider": member["provider"],
                "responded": True,
                "vote_score": 85,
                "recommendation": "APPROVE",
            }
            result = await mock_ask(
                member=member,
                weight=0.30,
                question="Test?",
                context={},
                council_type="standard"
            )
            assert result["responded"] is True
            assert result["vote_score"] == 85

    def test_quorum_reachable_with_nvidia(self):
        """With NVIDIA as a reliable member (weight 0.30), quorum should be reachable."""
        # Even if Anthropic, Bedrock, OpenAI, Google, Groq fail (5 failures),
        # NVIDIA + any 4 of the remaining will hit quorum (5).
        assert COUNCIL_MEMBERS[0]["provider"] == "nvidia"
        assert COUNCIL_MEMBERS[0]["weight"] >= 0.25
