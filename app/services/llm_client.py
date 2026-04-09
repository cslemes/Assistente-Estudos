"""
Factory for the shared LLM chat client.

Both Groq and OpenAI expose an identical `chat.completions.create()` interface,
so this module returns the raw client + resolved defaults for whichever provider
is selected via `settings.llm_provider`.

Usage:
    client, model, temperature, max_tokens = get_chat_client(settings)
    response = client.chat.completions.create(
        model=model, messages=[...], temperature=temperature, max_tokens=max_tokens
    )
"""

from app.config.settings import Settings


def get_chat_client(settings: Settings):
    """Return (client, model, temperature, max_tokens) for the active provider."""
    if settings.llm_provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        return (
            client,
            settings.openai_model,
            settings.openai_temperature,
            settings.openai_max_output_tokens,
        )
    else:  # groq (default)
        from groq import Groq
        client = Groq(api_key=settings.Groq_api_key)
        return (
            client,
            settings.Groq_model,
            settings.Groq_temperature,
            settings.Groq_max_output_tokens,
        )
