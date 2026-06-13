import logging

from openai import AsyncOpenAI

from app.graph.nodes.post_process import ClipService
from app.graph.state import AgentState
from app.services.llm import create_llm_client, get_embedding_model
from app.services.minio import download_media
from app.services.postgres import get_pool, vector_search

logger = logging.getLogger(__name__)


class L3SearchNode:
    def __init__(self):
        self._client: AsyncOpenAI | None = None

    async def _search_by_clip(
        self, media_url: str, conversation_id: str, cutoff: str
    ) -> list[dict]:
        """Search by CLIP visual embedding."""
        try:
            parts = media_url.split("/")
            bucket = parts[-2] if len(parts) >= 2 else "conversations-media"
            key = "/".join(parts[-2:])
            image_bytes = download_media(bucket, key)
            query_embedding = ClipService.embed_image(image_bytes)
            logger.info(f"[l3_search] CLIP embedding: {len(query_embedding)} dims")

            pool = await get_pool()
            rows = await pool.fetch(
                """SELECT content, media_url, media_type,
                         1 - (embedding_clip <=> $1::vector) AS score
                   FROM message_embeddings
                   WHERE conversation_id = $2 AND created_at < $3::timestamptz
                     AND embedding_clip IS NOT NULL
                     AND 1 - (embedding_clip <=> $1::vector) > 0.80
                   ORDER BY score DESC
                   LIMIT 5""",
                query_embedding,
                conversation_id,
                cutoff,
            )
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"[l3_search] CLIP error: {e}")
            return []

    async def _search_by_text(
        self, query_text: str, conversation_id: str, cutoff: str
    ) -> list[dict]:
        """Search by text embedding."""
        if self._client is None:
            self._client = create_llm_client()

        response = await self._client.embeddings.create(
            model=get_embedding_model(),
            input=query_text,
        )
        query_embedding = response.data[0].embedding
        results = await vector_search(
            conversation_id=conversation_id,
            embedding=query_embedding,
            cutoff=cutoff,
            limit=5,
            threshold=0.75,
        )
        logger.info(f"[l3_search] Text search returned {len(results)} results")
        return results

    async def run(self, state: AgentState) -> dict:
        query_text = state.get("parsed_content") or state.get("raw_content", "")
        media_url = state.get("media_url")

        if not query_text and not media_url:
            return {"l3_memories": []}

        # Cutoff: only search messages older than the L1 window
        cutoff = "NOW()"
        if state.get("l1_messages"):
            cutoff = str(state["l1_messages"][0].get("created_at", "NOW()"))

        memories = []

        # L3 search strategy depends on message type:
        # - Image messages: search by CLIP embedding (visual similarity)
        # - Text messages: search by text embedding (semantic similarity)
        # - Both: search by both and merge results

        if media_url and state.get("media_type") == "image":
            clip_results = await self._search_by_clip(
                media_url, state["conversation_id"], cutoff
            )
            memories.extend(clip_results)
            logger.info(f"[l3_search] CLIP search returned {len(clip_results)} results")

        if query_text:
            text_results = await self._search_by_text(
                query_text, state["conversation_id"], cutoff
            )
            memories.extend(text_results)

        # Deduplicate by removing exact content duplicates
        seen = set()
        unique_memories = []
        for m in memories:
            key = m.get("content", "")[:100]
            if key not in seen:
                seen.add(key)
                unique_memories.append(m)

        return {"l3_memories": unique_memories[:5]}
