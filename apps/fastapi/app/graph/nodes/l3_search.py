from openai import AsyncOpenAI

from app.graph.state import AgentState
from app.services.postgres import vector_search
from app.config import settings


class L3SearchNode:
    def __init__(self):
        self._client: AsyncOpenAI | None = None

    async def run(self, state: AgentState) -> dict:
        query_text = state.get("parsed_content") or state.get("raw_content", "")
        if not query_text:
            return {"l3_memories": []}

        try:
            if self._client is None:
                self._client = AsyncOpenAI(api_key=settings.openai_api_key)

            # Generate embedding for the query
            response = await self._client.embeddings.create(
                model=settings.openai_embedding_model,
                input=query_text,
            )
            query_embedding = response.data[0].embedding

            # Cutoff: only search messages older than the L1 window
            cutoff = "NOW()"
            if state.get("l1_messages"):
                last_msg = state["l1_messages"][0]
                cutoff = str(last_msg.get("created_at", "NOW()"))

            memories = await vector_search(
                conversation_id=state["conversation_id"],
                embedding=query_embedding,
                cutoff=cutoff,
                limit=5,
                threshold=0.75,
            )
            return {"l3_memories": memories}
        except Exception as e:
            print(f"[l3_search] Error: {e}")
            return {"l3_memories": []}
