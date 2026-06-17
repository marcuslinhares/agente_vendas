"""Jina AI multimodal embedding client (replaces local CLIP)."""

import base64
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class JinaEmbeddingError(Exception):
    pass


class JinaEmbeddingService:
    """Multimodal embeddings via Jina AI jina-clip-v2 (512d)."""

    def __init__(self) -> None:
        self._api_key = settings.jina_api_key
        self._base_url = settings.jina_base_url
        self._model = settings.jina_embedding_model
        self._dims = settings.jina_embedding_dims

    async def embed_image(self, image_bytes: bytes) -> list[float]:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "input": [{"image": b64}],
                    "dimensions": self._dims,
                    "normalized": True,
                },
            )
        if resp.status_code != 200:
            raise JinaEmbeddingError(f"Jina API error {resp.status_code}: {resp.text[:200]}")
        emb = resp.json()["data"][0]["embedding"]
        logger.info(f"[jina] Image embedding generated ({len(emb)} dims)")
        return emb
