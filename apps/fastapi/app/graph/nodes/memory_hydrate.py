from app.graph.state import AgentState
from app.services.postgres import get_last_messages, get_conversation_summary


class MemoryHydrateNode:
    async def run(self, state: AgentState) -> dict:
        conv_id = state["conversation_id"]

        # L1: Last 10 messages
        l1 = await get_last_messages(conv_id, limit=10)

        # L2: Conversation summary
        l2 = await get_conversation_summary(conv_id) or ""

        return {
            "l1_messages": l1,
            "l2_summary": l2,
        }
