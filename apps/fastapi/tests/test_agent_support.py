"""Unit tests for SupportAgentNode."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.graph.nodes.agent_support import SupportAgentNode
from app.graph.state import AgentState


def create_mock_state(**kwargs) -> AgentState:
    """Helper to create a default state with overrides."""
    state: AgentState = {
        "tenant_id": "test-tenant",
        "whatsapp_id": "5511999999999@c.us",
        "conversation_id": "test-conv-id",
        "message_id": "test-msg-id",
        "raw_content": "",
        "media_url": None,
        "media_type": None,
        "parsed_content": "",
        "intent": "support",
        "customer_id": None,
        "l1_messages": [],
        "l2_summary": "",
        "l3_memories": [],
        "l3_triggered": False,
        "selected_agent": "support",
        "agent_response": "",
        "tool_calls": [],
        "metadata": {},
        "embedding_clip": None,
        "embedding_text": None,
    }
    state.update(kwargs)
    return state


def test_build_system_prompt_without_summary():
    """Should build system prompt correctly without l2_summary."""
    node = SupportAgentNode()
    state = create_mock_state()

    prompt = node._build_system_prompt(state)

    assert "You are a customer support assistant" in prompt
    assert "Conversation summary:" not in prompt


def test_build_system_prompt_with_summary():
    """Should append l2_summary to system prompt if present."""
    node = SupportAgentNode()
    state = create_mock_state(l2_summary="O cliente está chateado com o atraso.")

    prompt = node._build_system_prompt(state)

    assert "You are a customer support assistant" in prompt
    assert "Conversation summary: O cliente está chateado com o atraso." in prompt


@pytest.mark.asyncio
async def test_run_uses_parsed_content():
    """Should use parsed_content when calling LLM."""
    node = SupportAgentNode()
    state = create_mock_state(
        parsed_content="Meu pedido ainda não chegou",
        raw_content="Onde tá meu bagulho????"
    )

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock()

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Vou verificar o status do seu pedido."
    mock_client.chat.completions.create.return_value = mock_response

    with (
        patch("app.graph.nodes.agent_support.create_llm_client", return_value=mock_client),
        patch("app.graph.nodes.agent_support.get_chat_model", return_value="test-model")
    ):
        result = await node.run(state)

        assert result["agent_response"] == "Vou verificar o status do seu pedido."
        assert result["tool_calls"] == []
        assert result["metadata"] == {"agent_type": "support"}

        mock_client.chat.completions.create.assert_awaited_once()
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "test-model"
        assert call_kwargs["messages"][1]["content"] == "Meu pedido ainda não chegou"


@pytest.mark.asyncio
async def test_run_uses_raw_content_if_no_parsed_content():
    """Should fallback to raw_content if parsed_content is missing."""
    node = SupportAgentNode()
    state = create_mock_state(
        parsed_content="",
        raw_content="Onde tá meu bagulho????"
    )

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock()

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Respondendo ao raw content."
    mock_client.chat.completions.create.return_value = mock_response

    with (
        patch("app.graph.nodes.agent_support.create_llm_client", return_value=mock_client),
        patch("app.graph.nodes.agent_support.get_chat_model", return_value="test-model")
    ):
        result = await node.run(state)

        assert result["agent_response"] == "Respondendo ao raw content."

        mock_client.chat.completions.create.assert_awaited_once()
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["messages"][1]["content"] == "Onde tá meu bagulho????"


@pytest.mark.asyncio
async def test_run_handles_empty_response():
    """Should use fallback message if LLM returns empty content."""
    node = SupportAgentNode()
    state = create_mock_state()

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock()

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = None
    mock_client.chat.completions.create.return_value = mock_response

    with (
        patch("app.graph.nodes.agent_support.create_llm_client", return_value=mock_client),
        patch("app.graph.nodes.agent_support.get_chat_model", return_value="test-model")
    ):
        result = await node.run(state)

        assert result["agent_response"] == "Desculpe, não consegui processar."


@pytest.mark.asyncio
async def test_run_initializes_client():
    """Should initialize the client only if it's None."""
    node = SupportAgentNode()
    state = create_mock_state()

    # Pre-set a client to test if create_llm_client is skipped
    mock_existing_client = MagicMock()
    mock_existing_client.chat.completions.create = AsyncMock()

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Resposta do client existente."
    mock_existing_client.chat.completions.create.return_value = mock_response

    node._client = mock_existing_client

    with (
        patch("app.graph.nodes.agent_support.create_llm_client") as mock_create_client,
        patch("app.graph.nodes.agent_support.get_chat_model", return_value="test-model")
    ):
        result = await node.run(state)

        # create_llm_client should not be called because _client was already set
        mock_create_client.assert_not_called()
        assert result["agent_response"] == "Resposta do client existente."
