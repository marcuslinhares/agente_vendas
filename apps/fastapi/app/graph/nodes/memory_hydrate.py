import asyncio

from app.graph.state import AgentState
from app.services.postgres import get_conversation_summary, get_last_messages


class MemoryHydrateNode:
    async def run(self, state: AgentState) -> dict:
        conv_id = state["conversation_id"]

        # Gather both queries concurrently
        l1, l2 = await asyncio.gather(
            get_last_messages(conv_id, limit=10), get_conversation_summary(conv_id)
        )

        l2 = l2 or ""

        return {
            "l1_messages": l1,
            "l2_summary": l2,
        }
