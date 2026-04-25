import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException

from app.config.settings import Settings
from app.models.api import SearchRequest, SearchResponse
from app.services.embedder import QueryEmbedder
from app.services.retriever import QdrantRetriever

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])


def get_settings():
    return Settings()


@lru_cache(maxsize=1)
def _get_embedder(dense: str, bm25: str, late: str) -> QueryEmbedder:
    return QueryEmbedder(dense_model_name=dense, bm25_model_name=bm25, late_interaction_model_name=late)


def get_embedder(settings: Settings = Depends(get_settings)):
    return _get_embedder(settings.dense_model_name, settings.bm25_model_name, settings.late_interaction_model_name)


def get_retriever(settings: Settings = Depends(get_settings)):
    return QdrantRetriever(settings=settings)


@router.post("", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    embedder: QueryEmbedder = Depends(get_embedder),
    retriever: QdrantRetriever = Depends(get_retriever),
):
    try:
        query_embeddings = embedder.embed_query(request.query)
        results = retriever.search_documents(
            embeddings=query_embeddings,
            limit=request.limit,
            topic=request.topic,
            course=request.course,
        )
        return SearchResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
