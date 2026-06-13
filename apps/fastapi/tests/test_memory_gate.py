from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.graph.nodes.memory_gate import MemoryGateNode
from app.graph.state import AgentState


@pytest.fixture
def base_state() -> AgentState:
    return {
        "whatsapp_id": "5511999999999@c.us",
        "conversation_id": "test-uuid",
        "message_id": "test-ulid",
        "raw_content": "User message",
        "media_url": None,
        "media_type": None,
        "parsed_content": "User message",
        "intent": "duvida",
        "customer_id": None,
        "l1_messages": [{"role": "user", "content": "hello"}],
        "l2_summary": "",
        "l3_memories": [],
        "l3_triggered": False,
        "agent_response": "",
        "tool_calls": [],
        "metadata": {},
        "embedding_clip": None,
        "embedding_text": None,
    }


@pytest.mark.asyncio
async def test_memory_gate_triggers_l3(base_state):
    """Should return l3_triggered=True when LLM decides it references history."""
    node = MemoryGateNode()

    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"trigger_l3": true, "reason": "Referenced"}'))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    with (
        patch("app.graph.nodes.memory_gate.create_llm_client", return_value=mock_client),
        patch("app.graph.nodes.memory_gate.settings.openai_api_key", "test-key"),
    ):
        result = await node.run(base_state)

        assert result["l3_triggered"] is True


@pytest.mark.asyncio
async def test_memory_gate_does_not_trigger_l3(base_state):
    """Should return l3_triggered=False when LLM decides it does not reference history."""
    node = MemoryGateNode()

    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"trigger_l3": false, "reason": "No reference"}'))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    with (
        patch("app.graph.nodes.memory_gate.create_llm_client", return_value=mock_client),
        patch("app.graph.nodes.memory_gate.settings.openai_api_key", "test-key"),
    ):
        result = await node.run(base_state)

        assert result["l3_triggered"] is False


@pytest.mark.asyncio
async def test_memory_gate_handles_malformed_json(base_state):
    """Should handle malformed JSON from LLM and return l3_triggered=False."""
    node = MemoryGateNode()

    mock_client = AsyncMock()
    mock_response = MagicMock()
    # Malformed JSON
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"trigger_l3": true, "reason": "Unclosed string'))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    with (
        patch("app.graph.nodes.memory_gate.create_llm_client", return_value=mock_client),
        patch("app.graph.nodes.memory_gate.settings.openai_api_key", "test-key"),
    ):
        result = await node.run(base_state)

        assert result["l3_triggered"] is False


@pytest.mark.asyncio
async def test_memory_gate_handles_api_error(base_state):
    """Should handle API exception and return l3_triggered=False."""
    node = MemoryGateNode()

    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = Exception("API error")

    with (
        patch("app.graph.nodes.memory_gate.create_llm_client", return_value=mock_client),
        patch("app.graph.nodes.memory_gate.settings.openai_api_key", "test-key"),
    ):
        result = await node.run(base_state)

        assert result["l3_triggered"] is False


@pytest.mark.asyncio
async def test_memory_gate_skips_when_no_api_key(base_state):
    """Should skip gate and return False when no API key is configured."""
    node = MemoryGateNode()

    with (
        patch("app.graph.nodes.memory_gate.settings.openai_api_key", None),
        patch("app.graph.nodes.memory_gate.settings.openrouter_api_key", None),
    ):
        result = await node.run(base_state)

        assert result["l3_triggered"] is False
