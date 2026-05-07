import logging
import time
from app.config.settings import Settings
from app.services.llm_client import get_chat_client

logger = logging.getLogger(__name__)


class SummarizerService:
    def __init__(self, settings: Settings):
        client, _, temperature, _ = get_chat_client(settings)
        self.client = client
        self.temperature = temperature
        self.model = (
            settings.summarize_groq_model
            if settings.llm_provider == "groq"
            else settings.summarize_openai_model
        )
        self.chunk_size = settings.summarize_chunk_size
        self.summarize_max_tokens = settings.summarize_max_tokens
        self.reduce_max_chars = settings.summarize_reduce_max_chars
        self.tpm_limit = settings.summarize_tpm_limit if settings.llm_provider == "groq" else None
        self.map_prompt = settings.summarize_map_prompt
        self.reduce_prompt = settings.summarize_reduce_prompt
        self._tokens_used_this_minute = 0
        self._minute_start = time.monotonic()

    def _wait_for_tpm(self, estimated_tokens: int):
        """Sleep if needed to avoid exceeding the TPM limit (Groq only)."""
        if self.tpm_limit is None:
            return

        elapsed = time.monotonic() - self._minute_start
        if elapsed >= 60:
            self._tokens_used_this_minute = 0
            self._minute_start = time.monotonic()

        if self._tokens_used_this_minute + estimated_tokens > self.tpm_limit:
            wait = 60 - elapsed
            logger.info("TPM limit approached — waiting %.1fs", wait)
            time.sleep(max(wait, 0))
            self._tokens_used_this_minute = 0
            self._minute_start = time.monotonic()

        self._tokens_used_this_minute += estimated_tokens

    def _call_llm(self, prompt: str) -> str:
        # ~4 chars per token; reserve output budget too
        estimated = len(prompt) // 4 + self.summarize_max_tokens
        self._wait_for_tpm(estimated)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.summarize_max_tokens,
        )
        content = response.choices[0].message.content

        # Refine the token count using actual usage if available
        if hasattr(response, "usage") and response.usage:
            actual = response.usage.total_tokens
            self._tokens_used_this_minute += actual - estimated

        return content

    def _chunk_text(self, text: str) -> list[str]:
        lines = text.splitlines(keepends=True)
        chunks = []
        current = []
        current_len = 0

        for line in lines:
            if current_len + len(line) > self.chunk_size and current:
                chunks.append("".join(current))
                current = []
                current_len = 0
            current.append(line)
            current_len += len(line)

        if current:
            chunks.append("".join(current))

        return chunks

    def _reduce(self, partials: list[str]) -> str:
        """Recursively reduce partial summaries, batching to stay under token limits."""
        combined = "\n\n---\n\n".join(partials)

        if len(combined) <= self.reduce_max_chars:
            return self._call_llm(self.reduce_prompt.format(partial_summaries=combined))

        # Too large — split into batches and reduce recursively
        batches: list[list[str]] = []
        current_batch: list[str] = []
        current_len = 0

        for p in partials:
            if current_len + len(p) > self.reduce_max_chars and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_len = 0
            current_batch.append(p)
            current_len += len(p)

        if current_batch:
            batches.append(current_batch)

        logger.info("Reduce: splitting into %d batch(es)", len(batches))
        intermediate = [self._reduce(batch) for batch in batches]
        return self._reduce(intermediate)

    def summarize(self, text: str) -> tuple[str, int]:
        """Return (summary, chunks_processed)."""
        chunks = self._chunk_text(text)
        logger.info("Summarizing %d chunk(s) with model %s", len(chunks), self.model)

        if len(chunks) == 1:
            summary = self._call_llm(self.map_prompt.format(chunk=text))
            return summary, 1

        partial = []
        for i, chunk in enumerate(chunks):
            logger.info("Map step %d/%d", i + 1, len(chunks))
            partial.append(self._call_llm(self.map_prompt.format(chunk=chunk)))

        logger.info("Reduce step — combining %d partial summaries", len(partial))
        summary = self._reduce(partial)
        return summary, len(chunks)
