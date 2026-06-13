"""Unit tests for FollowUpAgentNode."""

import pytest

from app.graph.nodes.agent_followup import FollowUpAgentNode
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
        "customer_id": "cust-123",
        "l1_messages": [],
        "l2_summary": "",
        "l3_memories": [],
        "l3_triggered": False,
        "selected_agent": "followup",
        "agent_response": "",
        "tool_calls": [],
        "metadata": {},
        "embedding_clip": None,
        "embedding_text": None,
    }


@pytest.mark.asyncio
async def test_followup_intent_followup(base_state):
    """Should return the correct response for 'followup' intent."""
    node = FollowUpAgentNode()
    base_state["intent"] = "followup"

    result = await node.run(base_state)

    expected = "Olá! Tudo bem? Só pra saber se de ajuda com nossos produtos."
    assert result["agent_response"] == expected
    assert result["tool_calls"] == []
    assert result["metadata"] == {"agent_type": "followup", "customer_id": "cust-123"}


@pytest.mark.asyncio
async def test_followup_intent_abandono(base_state):
    """Should return the correct response for 'abandono' intent."""
    node = FollowUpAgentNode()
    base_state["intent"] = "abandono"

    result = await node.run(base_state)

    expected = "Oi! Notei que você estava de olho nos produtos. Quer ajuda pra escolher?"
    assert result["agent_response"] == expected
    assert result["tool_calls"] == []
    assert result["metadata"] == {"agent_type": "followup", "customer_id": "cust-123"}


@pytest.mark.asyncio
async def test_followup_intent_promocao(base_state):
    """Should return the correct response for 'promocao' intent."""
    node = FollowUpAgentNode()
    base_state["intent"] = "promocao"

    result = await node.run(base_state)

    expected = "Temos promoções especiais esta semana! Quer conferir?"
    assert result["agent_response"] == expected
    assert result["tool_calls"] == []
    assert result["metadata"] == {"agent_type": "followup", "customer_id": "cust-123"}


@pytest.mark.asyncio
async def test_followup_intent_unknown(base_state):
    """Should return the default response for an unknown intent."""
    node = FollowUpAgentNode()
    base_state["intent"] = "unknown_intent"

    result = await node.run(base_state)

    expected = "Olá! Tudo bem? Só pra saber se de ajuda com nossos produtos."
    assert result["agent_response"] == expected
    assert result["tool_calls"] == []
    assert result["metadata"] == {"agent_type": "followup", "customer_id": "cust-123"}


@pytest.mark.asyncio
async def test_followup_no_customer_id(base_state):
    """Should handle missing customer_id gracefully."""
    node = FollowUpAgentNode()
    base_state["intent"] = "followup"
    base_state["customer_id"] = None

    result = await node.run(base_state)

    expected = "Olá! Tudo bem? Só pra saber se de ajuda com nossos produtos."
    assert result["agent_response"] == expected
    assert result["tool_calls"] == []
    assert result["metadata"] == {"agent_type": "followup", "customer_id": None}
