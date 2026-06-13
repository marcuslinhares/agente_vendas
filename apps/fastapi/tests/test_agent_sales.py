from unittest.mock import AsyncMock, patch

import pytest

from app.graph.nodes.agent_sales import SalesAgentNode
from app.graph.state import AgentState


@pytest.mark.asyncio
async def test_check_cache_simple_intents():
    node = SalesAgentNode()
    with patch("app.services.cache.get_cached_response", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = "Cached greeting"
        result = await node._check_cache("saudacao", "Olá")
        assert result == "Cached greeting"
        mock_get.assert_awaited_once_with("Olá")


@pytest.mark.asyncio
async def test_check_cache_complex_intents():
    node = SalesAgentNode()
    with patch("app.services.cache.get_cached_response", new_callable=AsyncMock) as mock_get:
        result = await node._check_cache("pedido", "Quero comprar")
        assert result is None
        mock_get.assert_not_called()


@pytest.mark.asyncio
async def test_set_cache_simple_intents():
    node = SalesAgentNode()
    with patch("app.services.cache.set_cached_response", new_callable=AsyncMock) as mock_set:
        await node._set_cache("saudacao", "Olá", "Olá, como posso ajudar?")
        mock_set.assert_awaited_once_with("Olá", "Olá, como posso ajudar?")


@pytest.mark.asyncio
async def test_set_cache_complex_intents():
    node = SalesAgentNode()
    with patch("app.services.cache.set_cached_response", new_callable=AsyncMock) as mock_set:
        await node._set_cache("pedido", "Quero comprar", "Claro, vamos fechar o pedido.")
        mock_set.assert_not_called()


@pytest.mark.asyncio
async def test_run_cache_hit():
    node = SalesAgentNode()
    state: AgentState = {
        "tenant_id": "tenant",
        "whatsapp_id": "123",
        "conversation_id": "abc",
        "message_id": "msg",
        "raw_content": "Olá",
        "media_url": None,
        "media_type": None,
        "parsed_content": "Olá",
        "intent": "saudacao",
        "customer_id": None,
        "l1_messages": [],
        "l2_summary": "",
        "l3_memories": [],
        "l3_triggered": False,
        "selected_agent": "sales",
        "agent_response": "",
        "tool_calls": [],
        "metadata": {},
        "embedding_clip": None,
        "embedding_text": None,
    }

    with patch.object(node, "_check_cache", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = "Cached greeting"
        with patch.object(node, "_client", new_callable=AsyncMock) as mock_client:
            result = await node.run(state)

            assert result["agent_response"] == "Cached greeting"
            assert result["metadata"]["cached"] is True
            mock_client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_run_cache_miss_simple_intent():
    node = SalesAgentNode()
    state: AgentState = {
        "tenant_id": "tenant",
        "whatsapp_id": "123",
        "conversation_id": "abc",
        "message_id": "msg",
        "raw_content": "Olá",
        "media_url": None,
        "media_type": None,
        "parsed_content": "Olá",
        "intent": "saudacao",
        "customer_id": None,
        "l1_messages": [],
        "l2_summary": "",
        "l3_memories": [],
        "l3_triggered": False,
        "selected_agent": "sales",
        "agent_response": "",
        "tool_calls": [],
        "metadata": {},
        "embedding_clip": None,
        "embedding_text": None,
    }

    class MockMessage:
        def __init__(self, content, tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls

        def model_dump(self):
            return {"role": "assistant", "content": self.content}

    class MockChoice:
        def __init__(self, message):
            self.message = message

    class MockResponse:
        def __init__(self, choices):
            self.choices = choices

    mock_llm_response = MockResponse([MockChoice(MockMessage("Generated greeting"))])

    with (
        patch.object(node, "_check_cache", new_callable=AsyncMock) as mock_check,
        patch.object(node, "_set_cache", new_callable=AsyncMock) as mock_set,
        patch("app.graph.nodes.agent_sales.get_chat_model", return_value="test-model"),
        patch("app.graph.nodes.agent_sales.create_llm_client") as mock_create_client,
        patch.object(node.tool_registry, "load_all", new_callable=AsyncMock) as mock_load,
    ):
        mock_check.return_value = None
        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_llm_response
        mock_create_client.return_value = mock_client
        mock_load.return_value = []

        result = await node.run(state)

        assert result["agent_response"] == "Generated greeting"
        mock_set.assert_awaited_once_with("saudacao", "Olá", "Generated greeting")
