import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.graph.nodes.l3_search import L3SearchNode
from app.graph.state import AgentState

@pytest.fixture
def empty_state() -> AgentState:
    return {
        "whatsapp_id": "test",
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
        "agent_response": "",
        "tool_calls": [],
        "metadata": {},
        "embedding_clip": None,
        "embedding_text": None,
    }

@pytest.mark.asyncio
async def test_run_no_query_and_no_media(empty_state):
    node = L3SearchNode()
    result = await node.run(empty_state)
    assert result == {"l3_memories": []}

@pytest.mark.asyncio
async def test_run_only_query_text(empty_state):
    node = L3SearchNode()
    state = empty_state.copy()
    state["parsed_content"] = "test query"

    with patch.object(node, "_search_by_text", new_callable=AsyncMock) as mock_text:
        mock_text.return_value = [{"content": "memory1"}]

        result = await node.run(state)

        assert result == {"l3_memories": [{"content": "memory1"}]}
        mock_text.assert_awaited_once_with("test query", "conv-123", "NOW()")

@pytest.mark.asyncio
async def test_run_only_media(empty_state):
    node = L3SearchNode()
    state = empty_state.copy()
    state["media_url"] = "http://test/conversations-media/img.jpg"
    state["media_type"] = "image"

    with patch.object(node, "_search_by_clip", new_callable=AsyncMock) as mock_clip:
        mock_clip.return_value = [{"content": "memory2"}]

        result = await node.run(state)

        assert result == {"l3_memories": [{"content": "memory2"}]}
        mock_clip.assert_awaited_once_with("http://test/conversations-media/img.jpg", "conv-123", "NOW()")

@pytest.mark.asyncio
async def test_run_both_deduplication(empty_state):
    node = L3SearchNode()
    state = empty_state.copy()
    state["parsed_content"] = "test query"
    state["media_url"] = "http://test/conversations-media/img.jpg"
    state["media_type"] = "image"

    with patch.object(node, "_search_by_text", new_callable=AsyncMock) as mock_text, \
         patch.object(node, "_search_by_clip", new_callable=AsyncMock) as mock_clip:

        mock_clip.return_value = [{"content": "memory1"}, {"content": "memory2"}]
        mock_text.return_value = [{"content": "memory2"}, {"content": "memory3"}]

        result = await node.run(state)

        # Should deduplicate memory2
        assert len(result["l3_memories"]) == 3
        contents = [m["content"] for m in result["l3_memories"]]
        assert contents == ["memory1", "memory2", "memory3"]

@pytest.mark.asyncio
@patch("app.graph.nodes.l3_search.download_media")
@patch("app.graph.nodes.l3_search.ClipService.embed_image")
@patch("app.graph.nodes.l3_search.get_pool")
async def test_search_by_clip(mock_get_pool, mock_embed_image, mock_download_media):
    node = L3SearchNode()

    mock_download_media.return_value = b"image_data"
    mock_embed_image.return_value = [0.1, 0.2]

    mock_pool = MagicMock()
    mock_pool.fetch = AsyncMock()
    mock_pool.fetch.return_value = [{"content": "clip_mem", "media_url": "url", "media_type": "image", "score": 0.9}]
    mock_get_pool.return_value = mock_pool

    result = await node._search_by_clip("http://test/bucket/image.jpg", "conv-123", "2023-01-01")

    mock_download_media.assert_called_once_with("bucket", "bucket/image.jpg")
    mock_embed_image.assert_called_once_with(b"image_data")
    mock_pool.fetch.assert_awaited_once()

    assert len(result) == 1
    assert result[0]["content"] == "clip_mem"

@pytest.mark.asyncio
@patch("app.graph.nodes.l3_search.download_media")
async def test_search_by_clip_exception(mock_download_media):
    node = L3SearchNode()

    # Force an exception
    mock_download_media.side_effect = Exception("Test error")

    result = await node._search_by_clip("http://test/bucket/image.jpg", "conv-123", "2023-01-01")

    assert result == []

@pytest.mark.asyncio
@patch("app.graph.nodes.l3_search.create_llm_client")
@patch("app.graph.nodes.l3_search.get_embedding_model")
@patch("app.graph.nodes.l3_search.vector_search")
async def test_search_by_text(mock_vector_search, mock_get_embedding_model, mock_create_llm_client):
    node = L3SearchNode()

    # Mock OpenAI client
    mock_client = MagicMock()
    mock_embeddings = AsyncMock()
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.3, 0.4])]
    mock_embeddings.create.return_value = mock_response
    mock_client.embeddings = mock_embeddings
    mock_create_llm_client.return_value = mock_client

    mock_get_embedding_model.return_value = "test-model"
    mock_vector_search.return_value = [{"content": "text_mem"}]

    result = await node._search_by_text("query", "conv-123", "2023-01-01")

    mock_create_llm_client.assert_called_once()
    mock_embeddings.create.assert_awaited_once_with(model="test-model", input="query")
    mock_vector_search.assert_awaited_once_with(
        conversation_id="conv-123",
        embedding=[0.3, 0.4],
        cutoff="2023-01-01",
        limit=5,
        threshold=0.75,
    )

    assert len(result) == 1
    assert result[0]["content"] == "text_mem"
