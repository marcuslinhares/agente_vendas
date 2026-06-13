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
        from app.graph.prompts import SALES_AGENT_SYSTEM_PROMPT

        intent = state.get("intent", "unknown")
        parts = [SALES_AGENT_SYSTEM_PROMPT.format(intent=intent)]

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

    async def _check_cache(self, intent: str, user_msg: str) -> str | None:
        """Check semantic cache for simple intents."""
        if intent not in {"saudacao", "agradecimento", "duvida"}:
            return None
        from app.services.cache import get_cached_response

        cached = await get_cached_response(user_msg)
        if cached:
            print(f"[sales_agent] Cache hit for '{intent}' intent")
        return cached

    async def _set_cache(self, intent: str, user_msg: str, content: str) -> None:
        """Cache successful responses for simple intents."""
        if intent not in {"saudacao", "agradecimento", "duvida"} or not content:
            return
        from app.services.cache import set_cached_response

        await set_cached_response(user_msg, content)

    async def _execute_tool_calls(self, msg, tool_calls_data: list[dict]) -> list[dict]:
        """Execute all tool calls in parallel and return tool result messages."""

        async def execute_tool(tc) -> dict:
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

        return await asyncio.gather(*[execute_tool(tc) for tc in msg.tool_calls])

    async def run(self, state: AgentState) -> dict:
        if self._client is None:
            self._client = create_llm_client()

        system_prompt = self._build_system_prompt(state)

        # Check semantic cache (only for simple intents — saves cost)
        user_msg = state.get("parsed_content") or state.get("raw_content", "")
        intent = state.get("intent", "")

        cached = await self._check_cache(intent, user_msg)
        if cached:
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
                "content": user_msg,
            },
        ]

        tool_calls_data: list[dict] = []
        turn = 0

        while turn < self.max_turns:
            turn += 1

            response = await self._client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                tools=tool_defs if tool_defs else None,  # type: ignore[arg-type]
                temperature=0.7,
            )

            msg = response.choices[0].message

            # If no tool calls, we're done — use this response
            if not msg.tool_calls:
                await self._set_cache(intent, user_msg, msg.content)  # type: ignore[arg-type,unused-coroutine]
                return {
                    "agent_response": msg.content
                    or "Desculpe, não consegui processar sua solicitação.",
                    "tool_calls": tool_calls_data,
                    "metadata": {"intent": intent, "turns": turn},
                }

            # Execute tool calls and append results
            messages.append(msg.model_dump())  # type: ignore[arg-type]
            results = await self._execute_tool_calls(msg, tool_calls_data)
            messages.extend(results)

        # If we hit max turns without a content response, use the last message
        return {
            "agent_response": msg.content
            if msg.content
            else "Processo concluído após múltiplas consultas.",
            "tool_calls": tool_calls_data,
            "metadata": {"intent": intent, "turns": turn, "truncated": True},
        }
