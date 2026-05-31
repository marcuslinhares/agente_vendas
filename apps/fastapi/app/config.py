from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Redis
    redis_url: str = "redis://localhost:6379"

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://app:localdev@localhost:5432/agentevendas"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

    # OpenRouter (optional, overrides OpenAI base URL when set)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "deepseek/deepseek-chat"  # cheap, strong tool use

    # LLM provider selection
    llm_provider: str = "openrouter"  # "openai" or "openrouter"

    # Streams
    stream_webhook: str = "webhook:incoming"
    stream_outbox: str = "whatsapp:outbox"
    stream_persist: str = "message:persist"
    consumer_group: str = "fastapi-workers"

    class Config:
        env_file = ".env"


settings = Settings()
