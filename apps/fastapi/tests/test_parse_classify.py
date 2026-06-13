"""Unit tests for ParseClassifyNode."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.graph.nodes.parse_classify import ParseClassifyNode
from app.graph.state import AgentState


@pytest.mark.asyncio
async def test_parse_classify_creates_conversation():
    """Should create a conversation for a new whatsapp_id."""
    node = ParseClassifyNode()

    state: AgentState = {
        "whatsapp_id": "5511999999999@c.us",
        "conversation_id": "",
        "message_id": "test-ulid",
        "raw_content": "Gostaria de saber mais sobre os produtos",
        "media_url": None,
        "media_type": None,
        "parsed_content": "",
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

    # Mock the postgres calls — patch where they are used (in parse_classify module)
    with patch(
        "app.graph.nodes.parse_classify.get_conversation_by_whatsapp",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = None
        with patch(
            "app.graph.nodes.parse_classify.create_conversation",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = {
                "id": "new-uuid",
                "status": "active",
                "message_count": 0,
            }

            result = await node.run(state)

            assert result["conversation_id"] == "new-uuid"
            assert result["parsed_content"] == "Gostaria de saber mais sobre os produtos"
            assert result["intent"] == "duvida"

            mock_get.assert_awaited_once_with("5511999999999@c.us")
            mock_create.assert_awaited_once_with("5511999999999@c.us")


@pytest.mark.asyncio
async def test_parse_classify_detects_order_intent():
    """Should detect 'pedido' intent when user mentions buying."""
    node = ParseClassifyNode()

    state: AgentState = {
        "whatsapp_id": "5511999999999@c.us",
        "conversation_id": "",
        "message_id": "test-ulid",
        "raw_content": "Quero comprar uma camiseta",
        "media_url": None,
        "media_type": None,
        "parsed_content": "",
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

    with patch(
        "app.graph.nodes.parse_classify.get_conversation_by_whatsapp",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = {
            "id": "existing-uuid",
            "status": "active",
            "message_count": 5,
        }
        with patch(
            "app.graph.nodes.parse_classify.create_conversation",
            new_callable=AsyncMock,
        ):
            result = await node.run(state)

            assert result["intent"] == "pedido"


@pytest.mark.asyncio
async def test_parse_classify_detects_greeting():
    """Should detect 'saudacao' intent for greetings."""
    node = ParseClassifyNode()

    state: AgentState = {
        "whatsapp_id": "5511999999999@c.us",
        "conversation_id": "",
        "message_id": "test-ulid",
        "raw_content": "Bom dia! Tudo bem?",
        "media_url": None,
        "media_type": None,
        "parsed_content": "",
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

    with patch(
        "app.graph.nodes.parse_classify.get_conversation_by_whatsapp",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = {
            "id": "existing-uuid",
            "status": "active",
            "message_count": 5,
        }
        with patch(
            "app.graph.nodes.parse_classify.create_conversation",
            new_callable=AsyncMock,
        ):
            result = await node.run(state)

            assert result["intent"] == "saudacao"


@pytest.mark.asyncio
async def test_parse_classify_reuses_existing_conversation():
    """Should use existing conversation when whatsapp_id is known."""
    node = ParseClassifyNode()

    state: AgentState = {
        "whatsapp_id": "5511988888888@c.us",
        "conversation_id": "",
        "message_id": "test-ulid-2",
        "raw_content": "Qual o preço?",
        "media_url": None,
        "media_type": None,
        "parsed_content": "",
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

    with patch(
        "app.graph.nodes.parse_classify.get_conversation_by_whatsapp",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = {
            "id": "existing-uuid-2",
            "status": "active",
            "message_count": 3,
        }
        with patch(
            "app.graph.nodes.parse_classify.create_conversation",
            new_callable=AsyncMock,
        ) as mock_create:
            result = await node.run(state)

            assert result["conversation_id"] == "existing-uuid-2"
            # Should NOT create a new conversation
            mock_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_parse_classify_detects_thanks():
    """Should detect 'agradecimento' intent."""
    node = ParseClassifyNode()

    state: AgentState = {
        "whatsapp_id": "5511999999999@c.us",
        "conversation_id": "",
        "message_id": "test-ulid",
        "raw_content": "Muito obrigado pela ajuda!",
        "media_url": None,
        "media_type": None,
        "parsed_content": "",
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

    with patch(
        "app.graph.nodes.parse_classify.get_conversation_by_whatsapp",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = {
            "id": "existing-uuid",
            "status": "active",
            "message_count": 5,
        }
        with patch(
            "app.graph.nodes.parse_classify.create_conversation",
            new_callable=AsyncMock,
        ):
            result = await node.run(state)

            assert result["intent"] == "agradecimento"


@pytest.mark.asyncio
async def test_parse_classify_describes_image_success():
    """Should download image and describe via Vision API."""
    node = ParseClassifyNode()

    mock_llm_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Uma camiseta vermelha de algodão."

    mock_create = AsyncMock(return_value=mock_response)
    mock_llm_client.chat.completions.create = mock_create

    with patch("app.graph.nodes.parse_classify.download_media") as mock_download:
        mock_download.return_value = b"fake-image-bytes"

        with patch("app.graph.nodes.parse_classify.create_llm_client") as mock_create_llm:
            mock_create_llm.return_value = mock_llm_client

            with patch("app.graph.nodes.parse_classify.get_chat_model") as mock_get_model:
                mock_get_model.return_value = "gpt-4o"

                result = await node._describe_image(
                    "http://minio/conversations-media/image.jpg", "Olha essa camiseta"
                )

                assert result == "Uma camiseta vermelha de algodão."

                mock_download.assert_called_once_with(
                    "conversations-media", "conversations-media/image.jpg"
                )
                mock_create_llm.assert_called_once()
                mock_create.assert_awaited_once()


@pytest.mark.asyncio
async def test_parse_classify_describes_image_fallback():
    """Should handle Vision API errors gracefully and return fallback string."""
    node = ParseClassifyNode()

    with patch("app.graph.nodes.parse_classify.download_media") as mock_download:
        mock_download.side_effect = Exception("MinIO offline")

        result = await node._describe_image(
            "http://minio/conversations-media/image.jpg", "Olha essa camiseta"
        )

        assert result == "[Imagem enviada pelo cliente: Olha essa camiseta]"
        mock_download.assert_called_once_with(
            "conversations-media", "conversations-media/image.jpg"
        )
