import json

from openai import AsyncOpenAI

from app.graph.state import AgentState
from app.tools.registry import ToolRegistry
from app.config import settings


class AgentExecuteNode:
    def __init__(self):
        self._client: AsyncOpenAI | None = None
        self.tool_registry = ToolRegistry()

    def _build_system_prompt(self, state: AgentState) -> str:
        parts = [
            "You are a sales assistant for a WhatsApp store in Brazil.",
            "You help customers find products, answer questions, and close orders.",
            "Always respond in Brazilian Portuguese (pt-BR).",
            f"Current intent: {state.get('intent', 'unknown')}",
            "",
        ]

        # L1: Recent messages
        if state.get("l1_messages"):
            parts.append("=== Recent conversation ===")
            for m in reversed(state["l1_messages"]):
                parts.append(f"{m['role']}: {str(m.get('content', ''))[:500]}")
            parts.append("")

        # L2: Summary
        if state.get("l2_summary"):
            parts.append(f"=== Conversation summary ===\n{state['l2_summary']}\n")

        # L3: Old memories
        if state.get("l3_memories"):
            parts.append("=== Relevant past context ===")
            for m in state["l3_memories"]:
                score = m.get("score", 0)
                parts.append(f"- {str(m.get('content', ''))[:300]} (relevance: {score:.2f})")
            parts.append("")

        return "\n".join(parts)

    async def run(self, state: AgentState) -> dict:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)

        system_prompt = self._build_system_prompt(state)

        # Load available tools
        tools = await self.tool_registry.load_all()
        tool_defs = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

        response = await self._client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": state.get("parsed_content") or state.get("raw_content", "")},
            ],
            tools=tool_defs if tool_defs else None,
            temperature=0.7,
        )

        msg = response.choices[0].message
        tool_calls_data = []

        # Execute any tool calls
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls_data.append({
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                })
                # Execute tool
                args = json.loads(tc.function.arguments)
                result = await self.tool_registry.execute(tc.function.name, args)
                # Note: in production, tool results would be fed back to LLM
                # for a proper multi-turn tool loop (future improvement)

        return {
            "agent_response": msg.content or "Desculpe, não consegui processar sua solicitação.",
            "tool_calls": tool_calls_data,
            "metadata": {"intent": state.get("intent", "unknown")},
        }
