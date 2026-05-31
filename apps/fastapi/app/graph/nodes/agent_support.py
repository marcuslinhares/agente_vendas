from app.graph.state import AgentState
from app.services.llm import create_llm_client, get_chat_model


class SupportAgentNode:
    """Lightweight agent for support questions (complaints, returns, technical)."""

    def __init__(self):
        self._client = None

    def _build_system_prompt(self, state: AgentState) -> str:
        parts = [
            "You are a customer support assistant for a WhatsApp store in Brazil.",
            "You handle: complaints, returns, technical issues, delivery status.",
            "Be empathetic and solution-oriented. Respond in Brazilian Portuguese.",
            "",
        ]

        if state.get("l2_summary"):
            parts.append(f"Conversation summary: {state['l2_summary']}")

        return "\n".join(parts)

    async def run(self, state: AgentState) -> dict:
        if self._client is None:
            self._client = create_llm_client()

        model = get_chat_model("suporte")
        system_prompt = self._build_system_prompt(state)

        response = await self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": state.get("parsed_content") or state.get("raw_content", ""),
                },
            ],
            temperature=0.5,
        )

        return {
            "agent_response": response.choices[0].message.content
            or "Desculpe, não consegui processar.",
            "tool_calls": [],
            "metadata": {"agent_type": "support"},
        }
