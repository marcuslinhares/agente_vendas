from app.tools.registry import ToolDef, ToolRegistry


async def _classify_client(params: dict) -> str:
    from app.services.postgres import get_pool

    pool = await get_pool()
    await pool.execute(
        "UPDATE conversations SET classification = $1, updated_at = NOW() WHERE id = $2",
        params.get("classification", "lead_morno"),
        params["conversation_id"],
    )
    return f"Cliente classificado como: {params.get('classification', 'lead_morno')}"


async def _schedule_followup(params: dict) -> str:
    return (
        f"Follow-up agendado para {params.get('days', 3)} dias. "
        f"Mensagem: {params.get('message_template', 'Olá! Como posso ajudar?')}"
    )


def register_customers_tools(registry: ToolRegistry) -> None:
    registry.register_core(
        ToolDef(
            name="classify_client",
            description="Classify a customer/lead in the CRM by conversation",
            parameters={
                "type": "object",
                "properties": {
                    "conversation_id": {"type": "string", "description": "Conversation ID"},
                    "classification": {
                        "type": "string",
                        "enum": ["lead_quente", "lead_morno", "lead_frio", "cliente"],
                        "description": "Customer classification",
                    },
                },
                "required": ["conversation_id", "classification"],
            },
            is_idempotent=True,
            execute=_classify_client,
        )
    )
    registry.register_core(
        ToolDef(
            name="schedule_followup",
            description="Schedule a follow-up message for a customer after N days",
            parameters={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Customer ID"},
                    "days": {
                        "type": "integer",
                        "default": 3,
                        "description": "Days until follow-up",
                    },
                    "message_template": {"type": "string", "description": "Message template"},
                },
            },
            is_idempotent=False,
            execute=_schedule_followup,
        )
    )
