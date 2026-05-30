from app.graph.state import AgentState
from app.services.postgres import get_conversation_by_whatsapp, create_conversation


class ParseClassifyNode:
    async def run(self, state: AgentState) -> dict:
        whatsapp_id = state["whatsapp_id"]

        # Get or create conversation
        conv = await get_conversation_by_whatsapp(whatsapp_id)
        if not conv:
            conv = await create_conversation(whatsapp_id)

        # If media, prepare a descriptive prefix
        parsed = state["raw_content"]
        if state.get("media_url") and state.get("media_type") == "image":
            # In production, GPT-4o Vision would describe the image here
            parsed = f"[Image sent by customer: {state['raw_content'] or 'no caption'}]"

        # Simple intent classification
        intent = "duvida"
        text = parsed.lower()
        if any(w in text for w in ["quero", "comprar", "pedir", "pedido"]):
            intent = "pedido"
        elif any(w in text for w in ["oi", "ola", "bom dia", "boa tarde", "hey"]):
            intent = "saudacao"
        elif any(w in text for w in ["obrigado", "valeu", "brigado"]):
            intent = "agradecimento"

        return {
            "conversation_id": conv["id"],
            "parsed_content": parsed,
            "intent": intent,
        }
