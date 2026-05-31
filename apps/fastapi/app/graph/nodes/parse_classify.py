import base64

from openai import AsyncOpenAI

from app.graph.state import AgentState
from app.services.postgres import get_conversation_by_whatsapp, create_conversation
from app.services.minio import download_media
from app.config import settings
from app.services.llm import create_llm_client, get_chat_model


class ParseClassifyNode:
    def __init__(self):
        self._client: AsyncOpenAI | None = None

    async def run(self, state: AgentState) -> dict:
        whatsapp_id = state["whatsapp_id"]

        # Get or create conversation
        conv = await get_conversation_by_whatsapp(whatsapp_id)
        if not conv:
            conv = await create_conversation(whatsapp_id)

        parsed = state["raw_content"]

        # If media, describe with GPT-4o Vision
        if state.get("media_url") and state.get("media_type") == "image":
            try:
                # Download image from MinIO
                url_path = state["media_url"]
                parts = url_path.split("/")
                bucket = parts[-2] if len(parts) >= 2 else "conversations-media"
                key = "/".join(parts[-2:])
                image_bytes = download_media(bucket, key)

                # Encode as base64
                b64 = base64.b64encode(image_bytes).decode("utf-8")

                if self._client is None:
                    self._client = create_llm_client()

                response = await self._client.chat.completions.create(
                    model=get_chat_model(),
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Descreva esta imagem em detalhes em português. "
                                            "Se for um produto, identifique cor, modelo, material, "
                                            "e qualquer característica visível.",
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{b64}",
                                        "detail": "low",
                                    },
                                },
                            ],
                        }
                    ],
                    max_tokens=300,
                )

                description = response.choices[0].message.content or ""
                parsed = f"[Imagem: {description}]"
                print(f"[parse_classify] Image described ({len(description)} chars)")

            except Exception as e:
                print(f"[parse_classify] Vision error: {e}")
                # Fallback to placeholder
                parsed = f"[Imagem enviada pelo cliente: {state['raw_content'] or 'sem legenda'}]"

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
