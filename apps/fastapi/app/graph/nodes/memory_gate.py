import json
import logging

from openai import AsyncOpenAI

from app.config import settings
from app.graph.state import AgentState
from app.services.llm import create_llm_client, get_memory_gate_model

logger = logging.getLogger(__name__)

class MemoryGateNode:
    def __init__(self):
        self._client: AsyncOpenAI | None = None

    async def _call_llm(self, user_msg: str, history: list[dict]) -> dict:
        if self._client is None:
            self._client = create_llm_client()

        messages_text = "\n".join(
            f"- {m['role']}: {str(m.get('content', ''))[:200]}"
            for m in history[-5:]  # last 5 messages for gate decision
        )

        prompt = (
            f"Analyze this user message in a sales conversation.\n\n"
            f'User message: "{user_msg}"\n\n'
            f"Recent messages:\n{messages_text}\n\n"
            f"Does the user's message reference something said earlier in the conversation "
            f"(more than 20 messages ago or in a previous session)?\n"
            f'Respond ONLY with JSON: {{"trigger_l3": true/false, "reason": "..."}}'
        )

        response = await self._client.chat.completions.create(
            model=get_memory_gate_model(),
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0,
        )

        return json.loads(response.choices[0].message.content)  # type: ignore[arg-type]

    async def run(self, state: AgentState) -> dict:
        if not settings.openai_api_key and not settings.openrouter_api_key:
            logger.warning("[memory_gate] No LLM API key configured — skipping gate")
            return {"l3_triggered": False}

        try:
            result = await self._call_llm(
                state.get("parsed_content") or state.get("raw_content", ""),
                state.get("l1_messages", []),
            )
            triggered = result.get("trigger_l3", False)
            if triggered:
                logger.info(f"[memory_gate] L3 triggered: {result.get('reason', '')}")
            return {"l3_triggered": triggered}
        except Exception as e:
            logger.error(f"[memory_gate] LLM error: {e}")
            return {"l3_triggered": False}
