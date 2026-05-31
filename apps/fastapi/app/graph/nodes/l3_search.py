from openai import AsyncOpenAI

from app.graph.state import AgentState
from app.services.postgres import vector_search
from app.services.minio import download_media
from app.graph.nodes.post_process import ClipService
from app.services.llm import create_llm_client, get_chat_model, get_embedding_model
from app.config import settings


class L3SearchNode:
    def __init__(self):
        self._client: AsyncOpenAI | None = None

    async def run(self, state: AgentState) -> dict:
        query_text = state.get("parsed_content") or state.get("raw_content", "")

        if not query_text and not state.get("media_url"):
            return {"l3_memories": []}

        try:
            has_image = state.get("media_url") and state.get("media_type") == "image"
            query_embedding_clip = None
            query_embedding_text = None

            # L3 search strategy depends on message type:
            # - Image messages: search by CLIP embedding (visual similarity)
            # - Text messages: search by text embedding (semantic similarity)
            # - Both: search by both and merge results

            if has_image:
                try:
                    # Download image and generate CLIP embedding
                    url_path = state["media_url"]
                    parts = url_path.split("/")
                    bucket = parts[-2] if len(parts) >= 2 else "conversations-media"
                    key = "/".join(parts[-2:])
                    image_bytes = download_media(bucket, key)
                    query_embedding_clip = ClipService.embed_image(image_bytes)
                    print(f"[l3_search] CLIP query embedding generated ({len(query_embedding_clip)} dims)")
                except Exception as e:
                    print(f"[l3_search] CLIP error: {e}")

            if query_text:
                if self._client is None:
                    self._client = create_llm_client()

                response = await self._client.embeddings.create(
                    model=get_embedding_model(),
                    input=query_text,
                )
                query_embedding_text = response.data[0].embedding

            # Cutoff: only search messages older than the L1 window
            cutoff = "NOW()"
            if state.get("l1_messages"):
                last_msg = state["l1_messages"][0]
                cutoff = str(last_msg.get("created_at", "NOW()"))

            memories = []

            # Search by CLIP (visual)
            if query_embedding_clip:
                from app.services.postgres import get_pool

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
                    query_embedding_clip, state["conversation_id"], cutoff,
                )
                clip_memories = [dict(r) for r in rows]
                memories.extend(clip_memories)
                print(f"[l3_search] CLIP search returned {len(clip_memories)} results")

            # Search by text (semantic)
            if query_embedding_text:
                text_results = await vector_search(
                    conversation_id=state["conversation_id"],
                    embedding=query_embedding_text,
                    cutoff=cutoff,
                    limit=5,
                    threshold=0.75,
                )
                memories.extend(text_results)
                print(f"[l3_search] Text search returned {len(text_results)} results")

            # Deduplicate by removing exact content duplicates
            seen = set()
            unique_memories = []
            for m in memories:
                key = m.get("content", "")[:100]
                if key not in seen:
                    seen.add(key)
                    unique_memories.append(m)

            return {"l3_memories": unique_memories[:5]}

        except Exception as e:
            print(f"[l3_search] Error: {e}")
            return {"l3_memories": []}
