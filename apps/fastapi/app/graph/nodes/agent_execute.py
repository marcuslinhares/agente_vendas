import json

from openai import AsyncOpenAI

from app.graph.state import AgentState
from app.tools.registry import ToolRegistry
from app.services.llm import create_llm_client, get_chat_model


class AgentExecuteNode:
    def __init__(self):
        self._client: AsyncOpenAI | None = None
        self.tool_registry = ToolRegistry()
        self.max_turns = 5

    def _build_system_prompt(self, state: AgentState) -> str:
        parts = [
            "You are a sales assistant for a WhatsApp store in Brazil.",
            "You help customers find products, answer questions, and close orders.",
            "Always respond in Brazilian Portuguese (pt-BR).",
            f"Current intent: {state.get('intent', 'unknown')}",
            "",
        ]

        # L1: Recent messages (fewer for simple intents to save tokens)
        intent = state.get("intent", "")
        max_l1 = 3 if intent in {"saudacao", "agradecimento"} else 10

        if state.get("l1_messages"):
            parts.append("=== Recent conversation ===")
            for m in reversed(state["l1_messages"][-max_l1:]):
                content = str(m.get("content", ""))[:300]
                parts.append(f"{m['role']}: {content}")
            parts.append("")

        # L2: Summary
        if state.get("l2_summary"):
            parts.append(f"=== Conversation summary ===\n{state['l2_summary']}\n")

        # L3: Old memories (truncated)
        if state.get("l3_memories"):
            parts.append("=== Relevant past context ===")
            for m in state["l3_memories"][:3]:  # max 3 memories
                score = m.get("score", 0)
                content = str(m.get("content", ""))[:200]
                parts.append(f"- {content} (relevance: {score:.2f})")
            parts.append("")

        return "\n".join(parts)

    async def run(self, state: AgentState) -> dict:
        if self._client is None:
            self._client = create_llm_client()

        system_prompt = self._build_system_prompt(state)
        model = get_chat_model(state.get("intent", ""))

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

        # Build messages array starting with system + user message
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": state.get("parsed_content") or state.get("raw_content", "")},
        ]

        tool_calls_data = []
        turn = 0

        while turn < self.max_turns:
            turn += 1

            response = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tool_defs if tool_defs else None,
                temperature=0.7,
            )

            msg = response.choices[0].message

            # If no tool calls, we're done — use this response
            if not msg.tool_calls:
                return {
                    "agent_response": msg.content or "Desculpe, não consegui processar sua solicitação.",
                    "tool_calls": tool_calls_data,
                    "metadata": {"intent": state.get("intent", "unknown"), "turns": turn},
                }

            # Execute tool calls and append results
            messages.append(msg)

            for tc in msg.tool_calls:
                tool_calls_data.append({
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                })

                try:
                    args = json.loads(tc.function.arguments)
                    result = await self.tool_registry.execute(tc.function.name, args)
                except Exception as e:
                    result = f"Error executing {tc.function.name}: {str(e)}"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result)[:2000],
                })

        # If we hit max turns without a content response, use the last message
        return {
            "agent_response": msg.content if msg.content else "Processo concluído após múltiplas consultas.",
            "tool_calls": tool_calls_data,
            "metadata": {"intent": state.get("intent", "unknown"), "turns": turn, "truncated": True},
        }
