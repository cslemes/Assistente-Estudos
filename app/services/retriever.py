import logging
from typing import List

from fastapi import HTTPException
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import Filter, FieldCondition, MatchValue, MatchAny

from app.config.settings import Settings
from app.models.embeddings import Document, QueryEmbeddings

logger = logging.getLogger(__name__)


class QdrantRetriever:
    def __init__(self, settings: Settings):
        client_params = {"url": settings.qdrant_url, "timeout": settings.qdrant_timeout}
        if settings.qdrant_api_key:
            client_params["api_key"] = settings.qdrant_api_key

        self.client = QdrantClient(**client_params)
        self.collection_name = settings.collection_name
        self.prefetch_limit = settings.prefetch_limit

    def _build_filter(self, topic: str = None, course: str = None) -> Filter | None:
        conditions = []
        if topic:
            conditions.append(FieldCondition(key="topic", match=MatchValue(value=topic)))
        if course:
            conditions.append(FieldCondition(key="course", match=MatchValue(value=course)))
        return Filter(must=conditions) if conditions else None

    def search_documents(
        self,
        embeddings: QueryEmbeddings,
        limit: int = 5,
        topic: str = None,
        course: str = None,
    ) -> List[Document]:
        query_filter = self._build_filter(topic=topic, course=course)
        try:
            search_result = self.client.query_points(
                collection_name=self.collection_name,
                prefetch=[
                    {"query": embeddings.dense, "using": "dense", "limit": self.prefetch_limit},
                    {"query": embeddings.sparse_bm25.model_dump(), "using": "sparse", "limit": self.prefetch_limit},
                ],
                query=embeddings.late,
                using="colbertv2.0",
                with_payload=True,
                limit=limit,
                query_filter=query_filter,
            )

            return [
                Document(
                    page_content=point.payload.get("text", ""),
                    metadata={
                        k: v for k, v in point.payload.items()
                        if k not in ("text",)
                    },
                )
                for point in search_result.points
            ]

        except UnexpectedResponse as e:
            logger.error("Qdrant search failed: %s", e)
            raise HTTPException(status_code=503, detail=f"Qdrant error: {e}")
        except Exception as e:
            logger.error("Unexpected error during search: %s", e)
            raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

    def scroll_visual(
        self,
        course: str,
        topic: str,
        aula_number: int,
    ) -> list[dict]:
        """Return all non-transcript chunks for a specific lesson, sorted by start_time."""
        conditions = [
            FieldCondition(key="course", match=MatchValue(value=course)),
            FieldCondition(key="topic", match=MatchValue(value=topic)),
            FieldCondition(key="aula_number", match=MatchValue(value=aula_number)),
            FieldCondition(key="source_type", match=MatchAny(any=["slide", "notebook", "whiteboard"])),
        ]
        query_filter = Filter(must=conditions)

        results = []
        offset = None
        try:
            while True:
                points, next_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=query_filter,
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )
                for p in points:
                    payload = p.payload or {}
                    results.append({
                        "source_type": payload.get("source_type"),
                        "text": payload.get("text", ""),
                        "start_time": payload.get("start_time"),
                        "video_url": payload.get("video_url"),
                        "slide_thumb": payload.get("slide_thumb"),
                    })
                if next_offset is None:
                    break
                offset = next_offset
        except Exception as e:
            logger.error("Qdrant scroll_visual failed: %s", e)
            raise HTTPException(status_code=503, detail=f"Qdrant error: {e}")

        return sorted(results, key=lambda x: (x["start_time"] is None, x["start_time"] or 0))
