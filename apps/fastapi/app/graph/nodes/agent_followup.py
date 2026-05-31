from app.graph.state import AgentState


class FollowUpAgentNode:
    """Simple agent for follow-up and lead nurturing (template-based)."""

    async def run(self, state: AgentState) -> dict:
        intent = state.get("intent", "")
        customer_id = state.get("customer_id")

        templates = {
            "followup": "Olá! Tudo bem? Só pra saber se de ajuda com nossos produtos.",
            "abandono": "Oi! Notei que você estava de olho nos produtos. Quer ajuda pra escolher?",
            "promocao": "Temos promoções especiais esta semana! Quer conferir?",
        }

        response = templates.get(intent, templates["followup"])

        return {
            "agent_response": response,
            "tool_calls": [],
            "metadata": {"agent_type": "followup", "customer_id": customer_id},
        }
