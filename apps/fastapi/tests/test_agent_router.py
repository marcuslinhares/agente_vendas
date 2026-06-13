"""Unit tests for AgentRouterNode."""

import pytest

from app.graph.nodes.agent_router import AgentRouterNode
from app.graph.state import AgentState


@pytest.fixture
def empty_state() -> AgentState:
    """Provides a basic empty state for testing."""
    return {
        "tenant_id": "test-tenant",
        "whatsapp_id": "5511999999999@c.us",
        "conversation_id": "test-conv-id",
        "message_id": "test-msg-id",
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
@pytest.mark.parametrize(
    "intent,expected_agent",
    [
        ("saudacao", "sales_agent"),
        ("pedido", "sales_agent"),
        ("duvida", "sales_agent"),
        ("agradecimento", "sales_agent"),
        ("reclamacao", "support_agent"),
        ("suporte", "support_agent"),
        ("troca", "support_agent"),
        ("followup", "followup_agent"),
    ],
)
async def test_agent_router_known_intents(
    empty_state: AgentState, intent: str, expected_agent: str
):
    """Should route known intents to their respective agents."""
    node = AgentRouterNode()
    state = empty_state.copy()
    state["intent"] = intent

    result = await node.run(state)

    assert result["selected_agent"] == expected_agent


@pytest.mark.asyncio
async def test_agent_router_missing_intent(empty_state: AgentState):
    """Should default to 'duvida' and route to 'sales_agent' if intent is missing."""
    node = AgentRouterNode()
    state = empty_state.copy()
    # Missing intent key shouldn't happen with TypedDict, but testing empty string
    state["intent"] = ""

    result = await node.run(state)

    # Empty string is not in the dictionary, so it falls back to the default 'sales_agent'
    assert result["selected_agent"] == "sales_agent"


@pytest.mark.asyncio
async def test_agent_router_unknown_intent(empty_state: AgentState):
    """Should fallback to 'sales_agent' for unknown intents."""
    node = AgentRouterNode()
    state = empty_state.copy()
    state["intent"] = "unknown_weird_intent"

    result = await node.run(state)

    assert result["selected_agent"] == "sales_agent"
