from typing import TypedDict, Optional


class AgentState(TypedDict):
    # Entry
    whatsapp_id: str
    conversation_id: str
    message_id: str
    raw_content: str
    media_url: Optional[str]
    media_type: Optional[str]

    # Parse
    parsed_content: str
    intent: str
    customer_id: Optional[str]

    # Memory
    l1_messages: list[dict]
    l2_summary: str
    l3_memories: list[dict]
    l3_triggered: bool

    # Execution
    agent_response: str
    tool_calls: list[dict]
    metadata: dict

    # Embeddings (generated in POST_PROCESS)
    embedding_clip: Optional[list[float]]
    embedding_text: Optional[list[float]]
