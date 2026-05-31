from typing import TypedDict


class AgentState(TypedDict):
    # Entry
    tenant_id: str
    whatsapp_id: str
    conversation_id: str
    message_id: str
    raw_content: str
    media_url: str | None
    media_type: str | None

    # Parse
    parsed_content: str
    intent: str
    customer_id: str | None

    # Memory
    l1_messages: list[dict]
    l2_summary: str
    l3_memories: list[dict]
    l3_triggered: bool

    # Routing
    selected_agent: str

    # Execution
    agent_response: str
    tool_calls: list[dict]
    metadata: dict

    # Embeddings (generated in POST_PROCESS)
    embedding_clip: list[float] | None
    embedding_text: list[float] | None
