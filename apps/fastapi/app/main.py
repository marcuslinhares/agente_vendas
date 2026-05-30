import asyncio
import ulid
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.services.redis import (
    ensure_consumer_group,
    consume_stream,
    publish_to_stream,
    ack_message,
)
from app.graph.agent import build_agent
from app.tools.registry import ToolRegistry
from app.tools.core import register_all_core_tools
from app.services.postgres import get_pool, increment_message_count

# Global instances
agent = None  # type: ignore
tool_registry = ToolRegistry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent

    # Initialize: register core tools, build agent
    register_all_core_tools(tool_registry)
    agent = build_agent()

    # Ensure consumer group exists
    await ensure_consumer_group(settings.stream_webhook, settings.consumer_group)

    # Start background consumer
    task = asyncio.create_task(stream_consumer())

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan, title="Agente de Vendas - LangGraph")


async def stream_consumer():
    """Background task: consume webhook:incoming, run agent, publish results."""
    consumer_id = f"consumer-{ulid.new().str}"

    async for msg_id, payload in consume_stream(
        settings.stream_webhook,
        settings.consumer_group,
        consumer_id,
    ):
        try:
            # Run agent
            state = await agent.ainvoke({
                "whatsapp_id": payload.get("whatsapp_id", ""),
                "conversation_id": payload.get("conversation_id", ""),
                "message_id": payload.get("id", ulid.new().str),
                "raw_content": payload.get("message", ""),
                "media_url": payload.get("media_url"),
                "media_type": payload.get("media_type"),
                "parsed_content": "",
                "intent": "",
                "customer_id": None,
                "l1_messages": [],
                "l2_summary": "",
                "l3_memories": [],
                "l3_triggered": False,
                "agent_response": "",
                "tool_calls": [],
                "metadata": {},
                "embedding_clip": None,
                "embedding_text": None,
            })

            # Publish response to outbox (Hono will send via Evolution API)
            await publish_to_stream(settings.stream_outbox, {
                "id": ulid.new().str,
                "to": payload["whatsapp_id"],
                "text": state.get("agent_response", ""),
            })

            # Publish to persist stream (NestJS will save to database)
            persist_payload = {
                "id": ulid.new().str,
                "conversation_id": state.get("conversation_id", ""),
                "role": "assistant",
                "content": state.get("agent_response", ""),
                "metadata": state.get("metadata", {}),
                "embedding_clip": state.get("embedding_clip"),
                "embedding_text": state.get("embedding_text"),
                "update_summary": False,
            }
            await publish_to_stream(settings.stream_persist, persist_payload)

            # Increment message count
            if state.get("conversation_id"):
                await increment_message_count(state["conversation_id"])

            await ack_message(settings.stream_webhook, settings.consumer_group, msg_id)

        except Exception as e:
            print(f"[consumer] Error processing {msg_id}: {e}")
            # Don't ack — will be retried or moved to dead-letter by Redis


@app.get("/health")
async def health():
    return {"status": "ok", "service": "fastapi-langgraph"}


@app.get("/ready")
async def ready():
    try:
        pool = await get_pool()
        await pool.fetchval("SELECT 1")
        return {"ready": True}
    except Exception as e:
        return {"ready": False, "error": str(e)}
