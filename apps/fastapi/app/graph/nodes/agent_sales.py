import asyncio
import json

from openai import AsyncOpenAI

from app.graph.state import AgentState
from app.services.llm import create_llm_client, get_chat_model
from app.tools.registry import ToolRegistry


class SalesAgentNode:
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

        # Check semantic cache (only for simple intents — saves cost)
        user_msg = state.get("parsed_content") or state.get("raw_content", "")
        intent = state.get("intent", "")

        if intent in {"saudacao", "agradecimento", "duvida"}:
            from app.services.cache import get_cached_response

            cached = await get_cached_response(user_msg)
            if cached:
                print(f"[sales_agent] Cache hit for '{intent}' intent")
                return {
                    "agent_response": cached,
                    "tool_calls": [],
                    "metadata": {"intent": intent, "cached": True},
                }

        model = get_chat_model(intent)

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
            {
                "role": "user",
                "content": state.get("parsed_content") or state.get("raw_content", ""),
            },
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
                # Cache successful responses for simple intents
                if intent in {"saudacao", "agradecimento", "duvida"} and msg.content:
                    from app.services.cache import set_cached_response

                    await set_cached_response(user_msg, msg.content)

                return {
                    "agent_response": msg.content
                    or "Desculpe, não consegui processar sua solicitação.",
                    "tool_calls": tool_calls_data,
                    "metadata": {"intent": intent, "turns": turn},
                }

            # Execute tool calls and append results
            messages.append(msg)

            # Execute all tool calls in parallel
            async def execute_tool(tc: any) -> dict:
                tool_calls_data.append(
                    {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                )

                try:
                    args = json.loads(tc.function.arguments)
                    result = await self.tool_registry.execute(tc.function.name, args)
                except Exception as e:
                    result = f"Error executing {tc.function.name}: {str(e)}"

                return {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result)[:2000],
                }

            results = await asyncio.gather(*[execute_tool(tc) for tc in msg.tool_calls])
            messages.extend(results)

        # If we hit max turns without a content response, use the last message
        return {
            "agent_response": msg.content
            if msg.content
            else "Processo concluído após múltiplas consultas.",
            "tool_calls": tool_calls_data,
            "metadata": {"intent": intent, "turns": turn, "truncated": True},
        }
