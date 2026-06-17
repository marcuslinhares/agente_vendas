"""Unit tests for L3SearchNode (Jina AI)."""

from unittest.mock import AsyncMock

import pytest

from app.graph.nodes.l3_search import L3SearchNode
from app.graph.state import AgentState


@pytest.fixture
def base_state() -> AgentState:
    return {
        "tenant_id": "test-tenant",
        "whatsapp_id": "5511999999999@c.us",
        "conversation_id": "conv-123",
        "message_id": "msg-123",
        "raw_content": "",
        "media_url": None,
        "media_type": None,
        "parsed_content": "",
        "intent": "",
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
async def test_l3_search_no_content(base_state):
    """Should return empty memories when no content or media."""
    node = L3SearchNode()
    result = await node.run(base_state)
    assert result["l3_memories"] == []


@pytest.mark.asyncio
async def test_l3_search_with_text(base_state, monkeypatch):
    """Should search by text when parsed_content is available."""

    async def mock_create(*args, **kwargs):
        class MockData:
            embedding = [0.2] * 1536

        class MockResponse:
            data = [MockData()]

        return MockResponse()

    monkeypatch.setattr(
        "app.graph.nodes.l3_search.create_llm_client",
        lambda: type(
            "MockClient",
            (),
            {"embeddings": type("MockEmb", (), {"create": mock_create})()},
        )(),
    )
    monkeypatch.setattr(
        "app.graph.nodes.l3_search.vector_search",
        AsyncMock(
            return_value=[
                {"content": "memory1", "media_url": None, "media_type": None, "score": 0.9}
            ]
        ),
    )

    state = base_state.copy()
    state["parsed_content"] = "Quero comprar um celular"

    node = L3SearchNode()
    result = await node.run(state)
    assert result["l3_memories"] == [
        {"content": "memory1", "media_url": None, "media_type": None, "score": 0.9}
    ]
