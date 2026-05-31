"""Voice processing: Whisper transcription and TTS."""

import io

from openai import AsyncOpenAI

from app.config import settings


class VoiceService:
    """Transcribes audio via Whisper and synthesizes speech via TTS."""

    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None

    async def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        return self._client

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.ogg") -> str:
        """Transcribe audio using Whisper via OpenAI."""
        client = await self._get_client()

        transcript = await client.audio.transcriptions.create(
            model="whisper-1",
            file=io.BytesIO(audio_bytes),
            language="pt",
        )
        return transcript.text

    async def synthesize(self, text: str, voice: str = "alloy") -> bytes:
        """Convert text to speech using OpenAI TTS."""
        client = await self._get_client()

        response = await client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text,
        )
        return response.content
