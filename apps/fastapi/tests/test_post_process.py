"""Unit tests for PostProcessNode (Jina AI)."""

import pytest

from app.graph.nodes.post_process import PostProcessNode
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
async def test_post_process_no_media(base_state):
    """Should return None embeddings when no media or text."""
    node = PostProcessNode()
    result = await node.run(base_state)
    assert result["embedding_clip"] is None
    assert result["embedding_text"] is None


@pytest.mark.asyncio
async def test_post_process_with_image(base_state, monkeypatch):
    """Should generate Jina embedding when media is an image."""

    async def mock_embed_image(self, image_bytes):
        return [0.1] * 512

    monkeypatch.setattr(
        "app.services.jina.JinaEmbeddingService.embed_image",
        mock_embed_image,
    )
    monkeypatch.setattr(
        "app.graph.nodes.post_process.download_media",
        lambda bucket, key: b"fake_image_bytes",
    )

    state = base_state.copy()
    state["media_url"] = "http://minio:9000/conversations-media/img.jpg"
    state["media_type"] = "image"

    node = PostProcessNode()
    result = await node.run(state)
    assert result["embedding_clip"] == [0.1] * 512
    assert result["embedding_text"] is None


@pytest.mark.asyncio
async def test_post_process_with_text(base_state, monkeypatch):
    """Should generate text embedding when parsed_content exists."""

    async def mock_create(*args, **kwargs):
        class MockData:
            embedding = [0.2] * 1536

        class MockResponse:
            data = [MockData()]

        return MockResponse()

    monkeypatch.setattr(
        "app.graph.nodes.post_process.create_llm_client",
        lambda: type(
            "MockClient",
            (),
            {"embeddings": type("MockEmb", (), {"create": mock_create})()},
        )(),
    )

    state = base_state.copy()
    state["parsed_content"] = "Um produto interessante"

    node = PostProcessNode()
    result = await node.run(state)
    assert result["embedding_clip"] is None
    assert result["embedding_text"] == [0.2] * 1536


@pytest.mark.asyncio
async def test_post_process_jina_error(base_state, monkeypatch):
    """Should handle Jina API error gracefully (return None, not crash)."""

    async def mock_embed_image(self, image_bytes):
        raise Exception("Jina API timeout")

    monkeypatch.setattr(
        "app.services.jina.JinaEmbeddingService.embed_image",
        mock_embed_image,
    )
    monkeypatch.setattr(
        "app.graph.nodes.post_process.download_media",
        lambda bucket, key: b"fake_image_bytes",
    )

    state = base_state.copy()
    state["media_url"] = "http://minio:9000/conversations-media/img.jpg"
    state["media_type"] = "image"

    node = PostProcessNode()
    result = await node.run(state)
    assert result["embedding_clip"] is None  # Graceful fallback
