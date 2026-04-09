from typing import List, AsyncGenerator
from app.models.embeddings import Document, format_context
from app.config.settings import Settings
from app.services.llm_client import get_chat_client
import logging
import json

logger = logging.getLogger(__name__)


class GroqService:
    def __init__(self, settings: Settings):
        self.client, self.default_model, self.default_temperature, self.default_max_output_tokens = get_chat_client(settings)
        self.system_prompt_template = settings.Groq_system_prompt

    def _build_messages(self, query: str, context_documents: List[Document]) -> list:
        context = format_context(context_documents)
        system_prompt = self.system_prompt_template.format(context=context, query=query)
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

    def generate_response(
        self,
        query: str,
        context_documents: List[Document],
        model: str = None,
        temperature: float = None,
        max_output_tokens: int = None,
    ) -> str:
        model = model or self.default_model
        temperature = temperature if temperature is not None else self.default_temperature
        max_output_tokens = max_output_tokens or self.default_max_output_tokens

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=self._build_messages(query, context_documents),
                temperature=temperature,
                max_tokens=max_output_tokens,
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error("Groq response generation failed", extra={"error": str(e), "query": query})
            raise Exception(f"Failed to generate response: {str(e)}")

    async def generate_stream_response(
        self,
        query: str,
        context_documents: List[Document],
        model: str = None,
        temperature: float = None,
        max_output_tokens: int = None,
    ) -> AsyncGenerator[str, None]:
        model = model or self.default_model
        temperature = temperature if temperature is not None else self.default_temperature
        max_output_tokens = max_output_tokens or self.default_max_output_tokens

        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=self._build_messages(query, context_documents),
                temperature=temperature,
                max_tokens=max_output_tokens,
                stream=True,
            )

            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield json.dumps({"type": "text_delta", "delta": delta})

            yield json.dumps({"type": "stream_completed"})

        except Exception as e:
            logger.error("Groq stream failed", extra={"error": str(e), "query": query})
            yield json.dumps({"type": "error", "message": str(e)})
