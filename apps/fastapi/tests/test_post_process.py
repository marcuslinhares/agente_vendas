from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.graph.nodes.post_process import ClipService, PostProcessNode


def test_clip_service_embed_image():
    # Mock instance to avoid loading open_clip
    mock_instance = {"preprocess": MagicMock(), "model": MagicMock()}
    mock_processed = MagicMock()
    mock_instance["preprocess"].return_value = mock_processed
    mock_processed.unsqueeze.return_value = mock_processed

    mock_embedding = MagicMock()
    mock_embedding.squeeze.return_value = mock_embedding
    mock_embedding.tolist.return_value = [0.1, 0.2, 0.3]
    mock_instance["model"].encode_image.return_value = mock_embedding

    with (
        patch.object(ClipService, "get_instance", return_value=mock_instance),
        patch("PIL.Image.open") as mock_open,
        patch("torch.no_grad"),
    ):
        mock_image = MagicMock()
        mock_open.return_value = mock_image
        mock_image.convert.return_value = mock_image

        result = ClipService.embed_image(b"test_image_bytes")

        assert result == [0.1, 0.2, 0.3]
        mock_open.assert_called_once()
        mock_image.convert.assert_called_once_with("RGB")
        mock_instance["preprocess"].assert_called_once_with(mock_image)
        mock_instance["model"].encode_image.assert_called_once_with(mock_processed)


@pytest.mark.asyncio
async def test_post_process_node_text_only():
    node = PostProcessNode()
    state = {
        "raw_content": "hello world",
        "parsed_content": "hello world parsed",
        "media_url": None,
        "media_type": None,
    }

    with patch.object(node, "_get_text_embedding", new_callable=AsyncMock) as mock_text_embed:
        mock_text_embed.return_value = [0.4, 0.5]

        result = await node.run(state)

        assert result["embedding_clip"] is None
        assert result["embedding_text"] == [0.4, 0.5]
        mock_text_embed.assert_awaited_once_with("hello world parsed")


@pytest.mark.asyncio
async def test_post_process_node_image_only():
    node = PostProcessNode()
    state = {
        "raw_content": "",
        "parsed_content": "",
        "media_url": "http://minio:9000/conversations-media/123/image.jpg",
        "media_type": "image",
    }

    with (
        patch("app.graph.nodes.post_process.download_media") as mock_download,
        patch.object(ClipService, "embed_image") as mock_embed_image,
    ):
        mock_download.return_value = b"image_bytes"
        mock_embed_image.return_value = [0.6, 0.7]

        result = await node.run(state)

        assert result["embedding_clip"] == [0.6, 0.7]
        assert result["embedding_text"] is None
        mock_download.assert_called_once_with("123", "123/image.jpg")
        mock_embed_image.assert_called_once_with(b"image_bytes")


@pytest.mark.asyncio
async def test_post_process_node_text_and_image():
    node = PostProcessNode()
    state = {
        "raw_content": "hello world",
        "parsed_content": "hello world parsed",
        "media_url": "http://minio:9000/my-bucket/folder/img.png",
        "media_type": "image",
    }

    with (
        patch.object(node, "_get_text_embedding", new_callable=AsyncMock) as mock_text_embed,
        patch("app.graph.nodes.post_process.download_media") as mock_download,
        patch.object(ClipService, "embed_image") as mock_embed_image,
    ):
        mock_text_embed.return_value = [0.4, 0.5]
        mock_download.return_value = b"image_bytes"
        mock_embed_image.return_value = [0.6, 0.7]

        result = await node.run(state)

        assert result["embedding_text"] == [0.4, 0.5]
        assert result["embedding_clip"] == [0.6, 0.7]
        mock_text_embed.assert_awaited_once_with("hello world parsed")
        mock_download.assert_called_once_with("folder", "folder/img.png")
        mock_embed_image.assert_called_once_with(b"image_bytes")


@pytest.mark.asyncio
async def test_post_process_node_error_handling():
    node = PostProcessNode()
    state = {
        "raw_content": "hello world",
        "parsed_content": "hello world parsed",
        "media_url": "http://minio:9000/bucket/img.png",
        "media_type": "image",
    }

    with (
        patch.object(node, "_get_text_embedding", new_callable=AsyncMock) as mock_text_embed,
        patch("app.graph.nodes.post_process.download_media") as mock_download,
    ):
        mock_text_embed.side_effect = Exception("Text API failed")
        mock_download.side_effect = Exception("Minio download failed")

        result = await node.run(state)

        # It should handle the exceptions smoothly and return Nones
        assert result["embedding_text"] is None
        assert result["embedding_clip"] is None
