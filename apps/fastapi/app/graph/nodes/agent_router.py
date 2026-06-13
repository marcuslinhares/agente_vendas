"""Routes requests to the appropriate specialized agent based on intent."""

import logging

from app.graph.state import AgentState

logger = logging.getLogger(__name__)


class AgentRouterNode:
    """Decides which specialist agent should handle this request."""

    def __init__(self):
        self._client = None

    async def run(self, state: AgentState) -> dict:
        intent = state.get("intent", "duvida")

        # Map intents to agents
        intent_to_agent = {
            "saudacao": "sales_agent",  # Simple greeting → sales
            "pedido": "sales_agent",  # Order request → sales
            "duvida": "sales_agent",  # Product question → sales
            "agradecimento": "sales_agent",  # Thanks → sales
            "reclamacao": "support_agent",  # Complaint → support
            "suporte": "support_agent",  # Support → support
            "troca": "support_agent",  # Exchange/return → support
            "followup": "followup_agent",  # Follow-up → followup
        }

        # If intent is clear from the message, route directly
        selected_agent = intent_to_agent.get(intent, "sales_agent")

        logger.info(f"[router] Intent '{intent}' → {selected_agent} agent")

        return {
            "selected_agent": selected_agent,
        }
