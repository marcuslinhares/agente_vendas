from unittest.mock import AsyncMock, patch

import pytest

from app.graph.nodes.post_process import PostProcessNode
from app.graph.state import AgentState


@pytest.mark.asyncio
async def test_post_process_text_embedding_fallback():
    """Should return None for embedding_text when text embedding generation fails."""
    node = PostProcessNode()

    state: AgentState = {
        "whatsapp_id": "5511999999999@c.us",
        "conversation_id": "test-uuid",
        "message_id": "test-ulid",
        "raw_content": "Test fallback",
        "media_url": None,
        "media_type": None,
        "parsed_content": "Test fallback",
        "intent": "",
        "customer_id": None,
        "l1_messages": [],
        "l2_summary": "",
        "l3_memories": [],
        "l3_triggered": False,
        "agent_response": "",
        "tool_calls": [],
        "metadata": {},
        "embedding_clip": None,
        "embedding_text": None,
    }

    with patch.object(node, "_get_text_embedding", new_callable=AsyncMock) as mock_embed:
        mock_embed.side_effect = Exception("Simulated embedding failure")

        result = await node.run(state)

        mock_embed.assert_awaited_once_with("Test fallback")
        assert result["embedding_text"] is None
        assert result["embedding_clip"] is None  # Assuming no media
