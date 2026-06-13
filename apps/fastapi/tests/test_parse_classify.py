"""Unit tests for ParseClassifyNode."""

from unittest.mock import AsyncMock, patch

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
async def test_parse_classify_handles_audio_success():
    """Should transcribe audio successfully via MinIO and Whisper."""
    node = ParseClassifyNode()

    state: AgentState = {
        "whatsapp_id": "5511999999999@c.us",
        "conversation_id": "existing-uuid",
        "message_id": "test-ulid",
        "raw_content": "",
        "media_url": "https://minio.example.com/my-bucket/audio.ogg",
        "media_type": "audio",
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
        "app.graph.nodes.parse_classify.get_conversation_by_whatsapp", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = {"id": "existing-uuid", "status": "active", "message_count": 5}
        with (
            patch("app.graph.nodes.parse_classify.create_conversation", new_callable=AsyncMock),
            patch("app.graph.nodes.parse_classify.download_media") as mock_download,
        ):
            mock_download.return_value = b"fake-audio-bytes"
            with patch("app.services.voice.VoiceService") as mock_voice_class:
                mock_voice_instance = AsyncMock()
                mock_voice_instance.transcribe.return_value = "This is a test transcript"
                mock_voice_class.return_value = mock_voice_instance

                result = await node.run(state)

                mock_download.assert_called_once_with("my-bucket", "my-bucket/audio.ogg")
                mock_voice_class.assert_called_once()
                mock_voice_instance.transcribe.assert_awaited_once_with(b"fake-audio-bytes")
                assert result["parsed_content"] == "[Áudio transcrito: This is a test transcript]"
                assert result["intent"] == "duvida"


@pytest.mark.asyncio
async def test_transcribe_audio_error_fallback():
    """Should return a fallback string when transcription fails."""
    node = ParseClassifyNode()

    state: AgentState = {
        "whatsapp_id": "5511999999999@c.us",
        "conversation_id": "existing-uuid",
        "message_id": "test-ulid",
        "raw_content": "Original text",
        "media_url": "https://minio.example.com/audio.ogg",
        "media_type": "audio",
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
        "app.graph.nodes.parse_classify.get_conversation_by_whatsapp", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = {"id": "existing-uuid", "status": "active", "message_count": 5}
        with (
            patch("app.graph.nodes.parse_classify.create_conversation", new_callable=AsyncMock),
            patch("app.graph.nodes.parse_classify.download_media") as mock_download,
        ):
            mock_download.side_effect = Exception("MinIO error")

            result = await node.run(state)

            assert mock_download.call_count == 1
            assert (
                result["parsed_content"]
                == "[Áudio transcrito: [Áudio enviado pelo cliente: Original text]]"
            )
