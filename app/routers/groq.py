import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
try:
    from langsmith import traceable
except ImportError:
    def traceable(**_kw):
        def _wrap(fn):
            return fn
        return _wrap

from functools import lru_cache

from app.config.settings import Settings
from app.models.api import OpenAIRequest, OpenAIResponse
from app.services.embedder import get_embedder_for_settings
from app.services.retriever import QdrantRetriever
from app.services.groq_service import GroqService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ask/groq", tags=["ask-groq"])


@lru_cache
def get_settings():
    return Settings()


@lru_cache
def get_embedder():
    settings = get_settings()
    return get_embedder_for_settings(settings)


@lru_cache
def get_groq_service():
    return GroqService(settings=get_settings())


def get_retriever(settings: Settings = Depends(get_settings)):
    return QdrantRetriever(settings=settings)


@traceable(name="groq_rag_pipeline")
@router.post("", response_model=OpenAIResponse)
async def ask_groq(
    request: OpenAIRequest,
    retriever: QdrantRetriever = Depends(get_retriever),
):
    try:
        embedder = get_embedder()
        groq_service = get_groq_service()
        query_embeddings = embedder.embed_query(request.query)
        context_documents = retriever.search_documents(
            embeddings=query_embeddings,
            limit=request.limit,
            topic=request.topic,
            course=request.course,
        )

        if not context_documents:
            logger.warning("No relevant documents found", extra={"query": request.query})

        answer = groq_service.generate_response(
            query=request.query,
            context_documents=context_documents,
            model=request.model,
            temperature=request.temperature,
            max_output_tokens=request.max_output_tokens,
        )
        return OpenAIResponse(answer=answer, source_documents=context_documents)

    except Exception as e:
        logger.error("Groq RAG pipeline failed", extra={"error": str(e), "query": request.query})
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {str(e)}")


@traceable(name="groq_rag_pipeline_stream")
@router.post("/stream")
async def ask_groq_stream(
    request: OpenAIRequest,
    retriever: QdrantRetriever = Depends(get_retriever),
):
    try:
        embedder = get_embedder()
        groq_service = get_groq_service()
        query_embeddings = embedder.embed_query(request.query)
        context_documents = retriever.search_documents(
            embeddings=query_embeddings,
            limit=request.limit,
            topic=request.topic,
            course=request.course,
        )

        if not context_documents:
            logger.warning("No relevant documents found", extra={"query": request.query})

        async def event_generator() -> AsyncGenerator[str, None]:
            try:
                yield f"data: {json.dumps({'type': 'source_documents', 'documents': [doc.model_dump() for doc in context_documents]})}\n\n"

                async for chunk in groq_service.generate_stream_response(
                    query=request.query,
                    context_documents=context_documents,
                    model=request.model,
                    temperature=request.temperature,
                    max_output_tokens=request.max_output_tokens,
                ):
                    yield f"data: {chunk}\n\n"

                yield f"data: {json.dumps({'type': 'stream_completed'})}\n\n"

            except Exception as e:
                logger.error("Groq stream generation failed", extra={"error": str(e)})
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    except Exception as e:
        logger.exception("Groq stream setup failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to start stream: {str(e)}")
