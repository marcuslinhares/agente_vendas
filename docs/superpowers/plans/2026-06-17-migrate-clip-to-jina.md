# Migracao CLIP Local para Jina AI Embedding Service

> **For agentic workers:** Use subagent-driven-development or executing-plans.

**Goal:** Replace local CLIP model (ViT-B-32 via open_clip_torch) with Jina AI jina-clip-v2 API for image embeddings, removing torch dependency and fixing product embedding bug.

**Architecture:** FastAPI calls Jina AI REST API for image embeddings instead of running CLIP locally. NestJS calls FastAPI POST /api/embed/product endpoint to get CLIP embeddings for products, replacing broken pending placeholder.

**Tech Stack:** Jina AI API, httpx, FastAPI, NestJS

---

## Chunk 1: Config + Service Layer

### Task 1: Add JINA_API_KEY to config

**File:** apps/fastapi/app/config.py

- [ ] Add to Settings class:

```python
    # Jina AI (multimodal embeddings)
    jina_api_key: str = ""
    jina_base_url: str = "https://api.jina.ai/v1"
    jina_embedding_model: str = "jina-clip-v2"
    jina_embedding_dims: int = 512
```

### Task 2: Remove CLIP deps from requirements.txt

**File:** apps/fastapi/requirements.txt

- [ ] Remove: open_clip_torch==2.24.0
- [ ] Remove: torch==2.4.0
- [ ] Remove: torchvision==0.19.0

### Task 3: Create Jina AI embedding service

**File:** CREATE apps/fastapi/app/services/jina.py

```python
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
                headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                json={"model": self._model, "input": [{"image": b64}], "dimensions": self._dims, "normalized": True},
            )
        if resp.status_code != 200:
            raise JinaEmbeddingError(f"Jina API error {resp.status_code}: {resp.text[:200]}")
        emb = resp.json()["data"][0]["embedding"]
        logger.info(f"[jina] Image embedding generated ({len(emb)} dims)")
        return emb
```

---

## Chunk 2: Update Graph Nodes

### Task 4: Update post_process.py

**File:** apps/fastapi/app/graph/nodes/post_process.py

- [ ] Remove CLipService class entirely
- [ ] Remove imports: open_clip, pillow_avif, torch, anyio, PIL
- [ ] Add import: from app.services.jina import JinaEmbeddingService
- [ ] In PostProcessNode.__init__, add self._jina = JinaEmbeddingService()
- [ ] Replace clip section: use await self._jina.embed_image(image_bytes) instead of anyio CLIP call

### Task 5: Update l3_search.py

**File:** apps/fastapi/app/graph/nodes/l3_search.py

- [ ] Replace: from app.graph.nodes.post_process import ClipService
  With: from app.services.jina import JinaEmbeddingService
- [ ] Add self._jina = JinaEmbeddingService() in __init__
- [ ] Change ClipService.embed_image(image_bytes) to await self._jina.embed_image(image_bytes)

---

## Chunk 3: Product Embedding Endpoint + NestJS

### Task 6: Create product embedding endpoint on FastAPI

**File:** apps/fastapi/app/main.py

- [ ] Add imports: from pydantic import BaseModel, from app.services.jina import JinaEmbeddingService
- [ ] Add POST /api/embed/product endpoint that:
  - Receives product_id, image_url (optional), text
  - If image_url: download from MinIO, call Jina embed_image()
  - Always: call OpenAI text-embedding-3-small for text
  - Returns {product_id, embedding_clip, embedding_text, error}

### Task 7: Update NestJS reindex.processor.ts

**File:** apps/nestjs/src/queue/reindex.processor.ts

- [ ] Inject HttpService from @nestjs/axios in constructor
- [ ] If @nestjs/axios not in package.json, add it
- [ ] Replace embeddingClip = pending block with HTTP call to FastAPI
- [ ] Import firstValueFrom from rxjs

---

## Chunk 4: Tests

### Task 8: Update post_process tests

**File:** apps/fastapi/tests/test_post_process.py

- [ ] Replace ClipService mocks with monkeypatch on JinaEmbeddingService.embed_image
- [ ] Add test: post_process_no_media returns None
- [ ] Add test: post_process_with_image returns Jina embedding
- [ ] Add test: post_process_jina_error graceful fallback

### Task 9: Update L3 search tests

**File:** apps/fastapi/tests/test_l3_search.py

- [ ] Replace ClipService mocks with monkeypatch on JinaEmbeddingService.embed_image

---

## Chunk 5: Cleanup + Verification

### Task 10: Run quality gates

- [ ] ruff check apps/fastapi/ -- no errors
- [ ] ruff format --check apps/fastapi/ -- no issues
- [ ] mypy apps/fastapi/app -- no errors
- [ ] cd apps/fastapi && python -m pytest tests/ -v --timeout=30 -- all pass

## Files Changed

| File | Action |
|------|--------|
| requirements.txt | Remove open_clip_torch, torch, torchvision |
| config.py | Add 4 Jina AI settings |
| app/services/jina.py | CREATE |
| app/graph/nodes/post_process.py | Replace CLIP with Jina, remove torch/pillow_avif |
| app/graph/nodes/l3_search.py | Replace CLIP with Jina |
| app/main.py | Add POST /api/embed/product |
| tests/test_post_process.py | Update mocks |
| tests/test_l3_search.py | Update mocks |
| reindex.processor.ts | Call FastAPI instead of pending |
| package.json (nestjs) | Add @nestjs/axios if needed |
