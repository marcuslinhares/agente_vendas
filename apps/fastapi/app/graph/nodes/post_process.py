from app.graph.state import AgentState
from app.services.minio import download_media
from app.config import settings


class ClipService:
    """Singleton CLIP model for image embeddings."""
    _instance = None

    @classmethod
    def get_instance(cls) -> dict:
        if cls._instance is None:
            import pillow_avif  # noqa: F401 — ensures AVIF support
            import open_clip
            import torch

            model, _, preprocess = open_clip.create_model_and_transforms(
                "ViT-B-32", pretrained="laion2b_s34b_b79k"
            )
            model.eval()
            cls._instance = {
                "model": model,
                "preprocess": preprocess,
            }
        return cls._instance

    @classmethod
    def embed_image(cls, image_bytes: bytes) -> list[float]:
        import io
        import torch
        from PIL import Image

        instance = cls.get_instance()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        processed = instance["preprocess"](image).unsqueeze(0)
        with torch.no_grad():
            embedding = instance["model"].encode_image(processed)
            return embedding.squeeze().tolist()


class PostProcessNode:
    def __init__(self) -> None:
        self._text_embedder = None

    async def _get_text_embedding(self, text: str) -> list[float]:
        from openai import AsyncOpenAI

        if self._text_embedder is None:
            self._text_embedder = AsyncOpenAI(api_key=settings.openai_api_key)

        response = await self._text_embedder.embeddings.create(
            model=settings.openai_embedding_model,
            input=text,
        )
        return response.data[0].embedding

    async def run(self, state: AgentState) -> dict:
        embedding_clip = None
        embedding_text = None

        # CLIP embedding for image media
        if state.get("media_url") and state.get("media_type") == "image":
            try:
                # Extract key from media URL
                # URL format: http://minio:9000/conversations-media/{key}
                url_path = state["media_url"]
                parts = url_path.split("/")
                bucket = parts[-2] if len(parts) >= 2 else "conversations-media"
                key = "/".join(parts[-2:])
                image_bytes = download_media(bucket, key)
                embedding_clip = ClipService.embed_image(image_bytes)
                print(f"[post_process] CLIP embedding generated ({len(embedding_clip)} dims)")
            except Exception as e:
                print(f"[post_process] CLIP error: {e}")

        # Text embedding
        source_text = state.get("parsed_content") or state.get("raw_content", "")
        if source_text:
            try:
                embedding_text = await self._get_text_embedding(source_text)
                print(f"[post_process] Text embedding generated ({len(embedding_text)} dims)")
            except Exception as e:
                print(f"[post_process] Text embedding error: {e}")

        return {
            "embedding_clip": embedding_clip,
            "embedding_text": embedding_text,
        }
