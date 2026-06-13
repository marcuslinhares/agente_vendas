import pytest
from unittest.mock import AsyncMock, patch

from app.graph.nodes.memory_gate import MemoryGateNode
from app.graph.state import AgentState

@pytest.fixture
def base_state() -> AgentState:
    return {
        "tenant_id": "default",
        "whatsapp_id": "5511999999999@c.us",
        "conversation_id": "test-conv",
        "message_id": "test-msg",
        "raw_content": "hello",
        "media_url": None,
        "media_type": None,
        "parsed_content": "hello",
        "intent": "greeting",
        "customer_id": None,
        "l1_messages": [],
        "l2_summary": "",
        "l3_memories": [],
        "l3_triggered": False,
        "selected_agent": "",
        "agent_response": "",
        "tool_calls": [],
        "metadata": {},
        "embedding_clip": None,
        "embedding_text": None,
    }

@pytest.mark.asyncio
async def test_memory_gate_exception_returns_false(base_state: AgentState):
    """Should return l3_triggered: False when _call_llm raises an exception."""
    node = MemoryGateNode()

    # Ensure api key is present so it doesn't skip
    with patch("app.graph.nodes.memory_gate.settings") as mock_settings:
        mock_settings.openai_api_key = "test-key"

        with patch.object(node, "_call_llm", new_callable=AsyncMock) as mock_call_llm:
            mock_call_llm.side_effect = Exception("API failure")

            result = await node.run(base_state)

            assert result == {"l3_triggered": False}
            mock_call_llm.assert_awaited_once_with("hello", [])
