import hashlib
import json
import logging
import random
import tempfile
from typing import Optional

from app.config.settings import Settings
from app.models.embeddings import Document
from app.services.llm_client import get_chat_client

logger = logging.getLogger(__name__)

MAX_SAMPLE_CHUNKS = 40
CHUNK_MAX_CHARS = 800

FLASHCARD_SYSTEM_PROMPT = """\
Você é um criador especializado de flashcards acadêmicos para o curso de \
Pós-Graduação em Inteligência Artificial da PUC-Rio.

Seu objetivo é transformar trechos de transcrições de aulas em pares de \
pergunta-resposta (flashcards) claros, objetivos e didáticos em português \
brasileiro.

Regras:
1. Cada flashcard deve testar um único conceito ou fato importante.
2. A pergunta (front) deve ser específica e sem ambiguidade.
3. A resposta (back) deve ser completa, mas concisa — máximo 3 linhas.
4. Priorize: definições, fórmulas, comparações entre algoritmos, \
   propriedades matemáticas, aplicações práticas.
5. Evite perguntas triviais como "O que o professor disse sobre X?".
6. Escreva sempre em português do Brasil.
7. Retorne SOMENTE um objeto JSON com uma chave "flashcards" cujo valor é \
   um array no formato: {"flashcards": [{"front": "...", "back": "..."}]}
"""

FLASHCARD_USER_TEMPLATE = """\
Com base nos trechos de aula abaixo, gere exatamente {num_cards} flashcards.

Retorne SOMENTE um JSON no formato:
{{"flashcards": [{{"front": "pergunta", "back": "resposta"}}]}}

{context}

Gere {num_cards} flashcards agora:
"""

ANKI_CSS = """\
.card {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 16px;
    color: #1a1a1a;
    background-color: #ffffff;
    padding: 20px;
    max-width: 600px;
    margin: 0 auto;
    line-height: 1.6;
}
.source {
    font-size: 11px;
    color: #888;
    margin-top: 16px;
    border-top: 1px solid #eee;
    padding-top: 8px;
}
"""


class FlashcardService:
    def __init__(self, settings: Settings):
        from qdrant_client import QdrantClient
        client_params: dict = {"url": settings.qdrant_url}
        if settings.qdrant_api_key:
            client_params["api_key"] = settings.qdrant_api_key
        self.qdrant = QdrantClient(**client_params)
        self.collection_name = settings.collection_name
        self.llm, self.model, self._temperature, self._max_tokens = get_chat_client(settings)

    def _build_filter(
        self,
        topic: Optional[str],
        course: Optional[str],
        aula_number: Optional[int],
    ):
        from qdrant_client.http.models import FieldCondition, Filter, MatchValue
        conditions = []
        if topic:
            conditions.append(FieldCondition(key="topic", match=MatchValue(value=topic)))
        if course:
            conditions.append(FieldCondition(key="course", match=MatchValue(value=course)))
        if aula_number is not None:
            # Stored as float in some payloads — try int first, float as fallback
            conditions.append(
                FieldCondition(key="aula_number", match=MatchValue(value=aula_number))
            )
        return Filter(must=conditions) if conditions else None

    def _ensure_indexes(self):
        """Create payload indexes if they don't exist yet."""
        from qdrant_client.http.models import PayloadSchemaType
        for field, schema in [
            ("course", PayloadSchemaType.KEYWORD),
            ("topic", PayloadSchemaType.KEYWORD),
            ("source_type", PayloadSchemaType.KEYWORD),
            ("aula_number", PayloadSchemaType.INTEGER),
        ]:
            try:
                self.qdrant.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field,
                    field_schema=schema,
                )
            except Exception:
                pass  # already exists

    def scroll_chunks(
        self,
        topic: Optional[str],
        course: Optional[str],
        aula_number: Optional[int],
        limit: int = MAX_SAMPLE_CHUNKS,
    ) -> list[Document]:
        self._ensure_indexes()
        query_filter = self._build_filter(topic, course, aula_number)
        results: list[Document] = []
        offset = None

        while len(results) < limit:
            batch_size = min(100, limit - len(results))
            points, next_offset = self.qdrant.scroll(
                collection_name=self.collection_name,
                scroll_filter=query_filter,
                with_payload=True,
                with_vectors=False,
                limit=batch_size,
                offset=offset,
            )
            for point in points:
                payload = point.payload or {}
                results.append(
                    Document(
                        page_content=payload.get("text", ""),
                        metadata={k: v for k, v in payload.items() if k != "text"},
                    )
                )
            if next_offset is None or not points:
                break
            offset = next_offset

        # If aula_number filter returned nothing, retry with float cast
        if not results and aula_number is not None:
            logger.debug("Retrying aula_number filter with float(%s)", aula_number)
            float_filter = self._build_filter_float(topic, course, aula_number)
            points, _ = self.qdrant.scroll(
                collection_name=self.collection_name,
                scroll_filter=float_filter,
                with_payload=True,
                with_vectors=False,
                limit=limit,
            )
            for point in points:
                payload = point.payload or {}
                results.append(
                    Document(
                        page_content=payload.get("text", ""),
                        metadata={k: v for k, v in payload.items() if k != "text"},
                    )
                )

        return results

    def _build_filter_float(
        self,
        topic: Optional[str],
        course: Optional[str],
        aula_number: Optional[int],
    ):
        from qdrant_client.http.models import FieldCondition, Filter, MatchValue
        conditions = []
        if topic:
            conditions.append(FieldCondition(key="topic", match=MatchValue(value=topic)))
        if course:
            conditions.append(FieldCondition(key="course", match=MatchValue(value=course)))
        if aula_number is not None:
            conditions.append(
                FieldCondition(key="aula_number", match=MatchValue(value=float(aula_number)))
            )
        return Filter(must=conditions) if conditions else None

    def _sample_chunks(self, docs: list[Document], num_cards: int) -> list[Document]:
        target = min(len(docs), max(num_cards * 2, 10))
        return random.sample(docs, target) if len(docs) > target else docs

    def _build_context(self, docs: list[Document]) -> str:
        parts = []
        for doc in docs:
            m = doc.metadata or {}
            label_parts = [p for p in [m.get("course"), m.get("topic")] if p]
            label = " — ".join(label_parts) or "Aula"
            aula = m.get("aula_number")
            aula_str = f" | Aula {int(aula)}" if aula is not None else ""
            text = (doc.page_content or "")[:CHUNK_MAX_CHARS]
            parts.append(f"[{label}{aula_str}]\n{text}")
        return "\n\n---\n\n".join(parts)

    def _generate_cards_from_llm(
        self, docs: list[Document], num_cards: int
    ) -> list[dict]:
        context = self._build_context(docs)
        user_prompt = FLASHCARD_USER_TEMPLATE.format(
            num_cards=num_cards,
            context=context,
        )
        response = self.llm.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": FLASHCARD_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=self._max_tokens,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        return self._parse_llm_output(raw)

    def _parse_llm_output(self, raw: str) -> list[dict]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error("LLM returned invalid JSON: %s", e)
            return []

        if isinstance(data, list):
            cards = data
        elif isinstance(data, dict):
            for key in ("flashcards", "cards", "items", "data"):
                if key in data and isinstance(data[key], list):
                    cards = data[key]
                    break
            else:
                logger.error("LLM JSON has no recognized array key: %s", list(data.keys()))
                return []
        else:
            return []

        return [
            {"front": str(item["front"]), "back": str(item["back"])}
            for item in cards
            if isinstance(item, dict) and "front" in item and "back" in item
        ]

    def _build_source_ref(
        self,
        topic: Optional[str],
        course: Optional[str],
        aula_number: Optional[int],
    ) -> str:
        parts = []
        if aula_number is not None:
            parts.append(f"Aula {aula_number}")
        if topic:
            parts.append(topic)
        if course:
            parts.append(course)
        return " — ".join(parts) if parts else "PUC-Rio IA"

    def _build_deck(
        self,
        cards: list[dict],
        deck_name: str,
        source_ref: str,
    ):
        import genanki
        deck_id = int(hashlib.md5(deck_name.encode()).hexdigest()[:8], 16)
        model_id = int(hashlib.md5(f"{deck_name}_model".encode()).hexdigest()[:8], 16)

        model = genanki.Model(
            model_id,
            "PUC-Rio Básico",
            fields=[
                {"name": "Front"},
                {"name": "Back"},
                {"name": "Source"},
            ],
            templates=[
                {
                    "name": "Card 1",
                    "qfmt": "{{Front}}",
                    "afmt": (
                        '{{FrontSide}}<hr id="answer">{{Back}}'
                        '<div class="source">{{Source}}</div>'
                    ),
                }
            ],
            css=ANKI_CSS,
        )

        deck = genanki.Deck(deck_id, deck_name)
        for card in cards:
            note = genanki.Note(
                model=model,
                fields=[card["front"], card["back"], source_ref],
            )
            deck.add_note(note)

        return deck

    def generate_apkg(
        self,
        topic: Optional[str],
        course: Optional[str],
        aula_number: Optional[int],
        num_cards: int,
        deck_name: Optional[str],
    ) -> str:
        all_docs = self.scroll_chunks(topic, course, aula_number)
        if not all_docs:
            raise ValueError("Nenhum trecho encontrado para os filtros fornecidos.")

        sampled = self._sample_chunks(all_docs, num_cards)
        cards = self._generate_cards_from_llm(sampled, num_cards)
        if not cards:
            raise RuntimeError(
                "O modelo não retornou flashcards válidos. Tente novamente."
            )

        source_ref = self._build_source_ref(topic, course, aula_number)
        resolved_deck_name = deck_name or source_ref or "PUC-Rio IA Flashcards"
        deck = self._build_deck(cards, resolved_deck_name, source_ref)

        import genanki
        package = genanki.Package(deck)
        tmp = tempfile.NamedTemporaryFile(
            suffix=".apkg",
            prefix="pucrio_flashcards_",
            delete=False,
        )
        tmp.close()
        package.write_to_file(tmp.name)
        logger.info("Generated %d flashcards → %s", len(cards), tmp.name)
        return tmp.name
