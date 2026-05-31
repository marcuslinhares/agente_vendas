"""Unified LLM client with model routing by task complexity."""

from openai import AsyncOpenAI
from app.config import settings

# Simple intents that don't need a powerful model
SIMPLE_INTENTS = {"saudacao", "agradecimento", "despedida", "menu"}
# Memory gate is always a simple binary decision
MEMORY_GATE_SIMPLE = True


def create_llm_client() -> AsyncOpenAI:
    """Create an AsyncOpenAI client configured for the selected provider."""
    if settings.llm_provider == "openrouter" and settings.openrouter_api_key:
        return AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )
    return AsyncOpenAI(api_key=settings.openai_api_key)


def get_chat_model(intent: str = "") -> str:
    """
    Return the model name based on intent complexity.
    Simple intents use the cheap model; complex ones use the full model.
    """
    if intent and intent.lower() in SIMPLE_INTENTS:
        if settings.llm_provider == "openrouter":
            return "deepseek/deepseek-v4-flash"
        return "gpt-4o-mini"

    if settings.llm_provider == "openrouter":
        return settings.openrouter_model
    return settings.openai_model


def get_embedding_model() -> str:
    return settings.openai_embedding_model


def get_memory_gate_model() -> str:
    """Memory gate is a simple binary decision — use cheapest model."""
    if settings.llm_provider == "openrouter":
        return "deepseek/deepseek-v4-flash"
    return "gpt-4o-mini"
