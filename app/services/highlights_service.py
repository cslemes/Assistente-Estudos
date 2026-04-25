import json
import logging
import time

from app.config.settings import Settings
from app.services.llm_client import get_chat_client

logger = logging.getLogger(__name__)

MAP_PROMPT = """\
Você é um assistente acadêmico analisando a transcrição de uma aula de Pós-Graduação em IA.
Identifique de 0 a 2 momentos-chave neste trecho — momentos onde um conceito é claramente \
definido, explicado ou demonstrado pelo professor.

Trecho (timestamps em segundos):
{chunk}

Retorne SOMENTE JSON válido, sem markdown:
{{"highlights": [{{"title": "...", "description": "...", "start_time": 0}}]}}
Se não houver momentos relevantes, retorne: {{"highlights": []}}"""

REDUCE_PROMPT = """\
Você é um assistente acadêmico. Abaixo estão candidatos a momentos-chave de uma aula longa.
Selecione os {n} mais importantes e distintos, evitando duplicatas e priorizando conceitos \
diferentes entre si.

Candidatos:
{candidates}

Retorne SOMENTE JSON válido, sem markdown:
{{"highlights": [{{"title": "...", "description": "...", "start_time": 0}}]}}"""

CHUNK_SIZE = 3000  # chars per map chunk
MAX_TOKENS = 512


class HighlightsService:
    def __init__(self, settings: Settings):
        self.client, _, self.temperature, _ = get_chat_client(settings)
        self.model = (
            settings.summarize_groq_model
            if settings.llm_provider == "groq"
            else settings.summarize_openai_model
        )
        self._tokens_used = 0
        self._minute_start = time.monotonic()
        self.tpm_limit = settings.summarize_tpm_limit

    def _wait_for_tpm(self, estimated: int):
        elapsed = time.monotonic() - self._minute_start
        if elapsed >= 60:
            self._tokens_used = 0
            self._minute_start = time.monotonic()
        if self._tokens_used + estimated > self.tpm_limit:
            wait = 60 - elapsed
            logger.info("TPM limit approached — waiting %.1fs", wait)
            time.sleep(max(wait, 0))
            self._tokens_used = 0
            self._minute_start = time.monotonic()
        self._tokens_used += estimated

    def _call_llm(self, prompt: str) -> str:
        estimated = len(prompt) // 4 + MAX_TOKENS
        self._wait_for_tpm(estimated)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=MAX_TOKENS,
        )
        return response.choices[0].message.content

    def _parse_json(self, raw: str) -> list[dict]:
        try:
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            highlights = json.loads(text).get("highlights", [])
            for h in highlights:
                if "start_time" in h:
                    h["start_time"] = int(h["start_time"])
            return highlights
        except Exception:
            logger.warning("Failed to parse highlights JSON: %s", raw[:200])
            return []

    def _format_chunk(self, utterances: list[dict]) -> str:
        lines = []
        for u in utterances:
            start = int(u.get("start", 0))
            mm, ss = divmod(start, 60)
            text = u.get("text", u.get("word", "")).strip()
            speaker = u.get("speaker", "")
            prefix = f"[{mm}:{ss:02d}]" + (f" {speaker}:" if speaker else "")
            lines.append(f"{prefix} {text}")
        return "\n".join(lines)

    def _chunk_utterances(self, utterances: list[dict]) -> list[list[dict]]:
        chunks, current, current_len = [], [], 0
        for u in utterances:
            text = u.get("text", u.get("word", ""))
            if current_len + len(text) > CHUNK_SIZE and current:
                chunks.append(current)
                current, current_len = [], 0
            current.append(u)
            current_len += len(text)
        if current:
            chunks.append(current)
        return chunks

    def _map(self, utterances: list[dict]) -> list[dict]:
        chunks = self._chunk_utterances(utterances)
        candidates = []
        for i, chunk in enumerate(chunks):
            logger.info("Highlights map %d/%d", i + 1, len(chunks))
            formatted = self._format_chunk(chunk)
            raw = self._call_llm(MAP_PROMPT.format(chunk=formatted))
            candidates.extend(self._parse_json(raw))
        return candidates

    def _reduce(self, candidates: list[dict], n: int) -> list[dict]:
        if len(candidates) <= n:
            return candidates
        logger.info("Highlights reduce: %d candidates → top %d", len(candidates), n)
        formatted = json.dumps(candidates, ensure_ascii=False, indent=2)
        raw = self._call_llm(REDUCE_PROMPT.format(n=n, candidates=formatted))
        return self._parse_json(raw)

    def extract(self, transcription: dict, n: int = 5) -> list[dict]:
        segments_json = transcription.get("segments_json")
        video_url = transcription.get("video_url")

        if segments_json:
            utterances = json.loads(segments_json)
        else:
            # Fallback: split plain text into fake utterances with no timestamps
            text = transcription.get("text", "")
            words = text.split()
            utterances = [{"text": " ".join(words[i:i+50]), "start": 0}
                          for i in range(0, len(words), 50)]

        candidates = self._map(utterances)
        highlights = self._reduce(candidates, n)

        # Attach deep links
        for h in highlights:
            start = h.get("start_time", 0)
            if video_url and start is not None:
                base = video_url.split("?")[0]
                h["video_url"] = f"{base}?t={start}"
            else:
                h["video_url"] = None

        logger.info("Extracted %d highlight(s)", len(highlights))
        return highlights
