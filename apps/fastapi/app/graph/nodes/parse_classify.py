import base64

from openai import AsyncOpenAI

from app.config import settings
from app.graph.state import AgentState
from app.services.llm import create_llm_client, get_chat_model
from app.services.minio import download_media
from app.services.postgres import create_conversation, get_conversation_by_whatsapp


class ParseClassifyNode:
    def __init__(self):
        self._client: AsyncOpenAI | None = None

    async def _describe_image(self, media_url: str, raw_content: str) -> str:
        """Download image from MinIO and describe via Vision API."""
        try:
            parts = media_url.split("/")
            bucket = parts[-2] if len(parts) >= 2 else "conversations-media"
            key = "/".join(parts[-2:])
            image_bytes = download_media(bucket, key)

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
                                "text": (
                                    "Descreva esta imagem em detalhes em português. "
                                    "Se for um produto, identifique cor, modelo, material, "
                                    "e qualquer característica visível."
                                ),
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
            print(f"[parse_classify] Image described ({len(description)} chars)")
            return description
        except Exception as e:
            print(f"[parse_classify] Vision error: {e}")
            return f"[Imagem enviada pelo cliente: {raw_content or 'sem legenda'}]"

    async def _transcribe_audio(self, media_url: str, raw_content: str) -> str:
        """Download audio from MinIO and transcribe via Whisper."""
        try:
            parts = media_url.split("/")
            bucket = parts[-2] if len(parts) >= 2 else "conversations-media"
            key = "/".join(parts[-2:])
            audio_bytes = download_media(bucket, key)

            from app.services.voice import VoiceService

            voice = VoiceService()
            transcript = await voice.transcribe(audio_bytes)
            print(f"[parse_classify] Audio transcribed ({len(transcript)} chars)")
            return transcript
        except Exception as e:
            print(f"[parse_classify] Transcription error: {e}")
            return f"[Áudio enviado pelo cliente: {raw_content or 'sem transcrição'}]"

    _PEDIDO_WORDS = ("quero", "comprar", "pedir", "pedido")
    _SAUDACAO_WORDS = ("oi", "ola", "bom dia", "boa tarde", "hey")
    _AGRADECIMENTO_WORDS = ("obrigado", "valeu", "brigado")

    def _classify_intent(self, text: str) -> str:
        """Classify user intent based on message content."""
        text_lower = text.lower()
        for w in self._PEDIDO_WORDS:
            if w in text_lower:
                return "pedido"
        for w in self._SAUDACAO_WORDS:
            if w in text_lower:
                return "saudacao"
        for w in self._AGRADECIMENTO_WORDS:
            if w in text_lower:
                return "agradecimento"
        return "duvida"

    async def run(self, state: AgentState) -> dict:
        whatsapp_id = state["whatsapp_id"]

        # Tenant resolution (when multitenancy is enabled)
        tenant_id = state.get("tenant_id", settings.default_tenant_id)
        if settings.enable_multitenancy:
            print(f"[parse_classify] Tenant: {tenant_id}")

        # Get or create conversation
        conv = await get_conversation_by_whatsapp(whatsapp_id)
        if not conv:
            conv = await create_conversation(whatsapp_id)

        parsed = state["raw_content"]
        media_url = state.get("media_url")
        media_type = state.get("media_type")

        # If media, describe with Vision API or transcribe with Whisper
        if media_url and media_type == "image":
            description = await self._describe_image(media_url, state["raw_content"])
            parsed = f"[Imagem: {description}]"

        elif media_url and media_type == "audio":
            transcript = await self._transcribe_audio(media_url, state["raw_content"])
            parsed = f"[Áudio transcrito: {transcript}]"

        # Simple intent classification
        intent = self._classify_intent(parsed)

        return {
            "conversation_id": conv["id"],
            "parsed_content": parsed,
            "intent": intent,
        }
