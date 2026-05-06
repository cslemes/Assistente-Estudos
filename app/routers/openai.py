import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langsmith import traceable

from app.config.settings import Settings
from app.models.api import OpenAIRequest, OpenAIResponse
from app.services.embedder import get_embedder_for_settings
from app.services.retriever import QdrantRetriever
from app.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ask", tags=["ask"])


def get_settings():
    return Settings()


def get_embedder(settings: Settings = Depends(get_settings)):
    return get_embedder_for_settings(settings)


def get_retriever(settings: Settings = Depends(get_settings)):
    return QdrantRetriever(settings=settings)


def get_openai_service(settings: Settings = Depends(get_settings)):
    return OpenAIService(settings=settings)


@traceable(name="rag_pipeline")
@router.post("", response_model=OpenAIResponse)
async def ask(
    request: OpenAIRequest,
    embedder=Depends(get_embedder),
    retriever: QdrantRetriever = Depends(get_retriever),
    openai_service: OpenAIService = Depends(get_openai_service),
):
    try:
        query_embeddings = embedder.embed_query(request.query)
        context_documents = retriever.search_documents(
            embeddings=query_embeddings,
            limit=request.limit,
            topic=request.topic,
            course=request.course,
        )

        if not context_documents:
            logger.warning("No relevant documents found", extra={"query": request.query})

        answer = openai_service.generate_response(
            query=request.query,
            context_documents=context_documents,
            model=request.model,
            temperature=request.temperature,
            max_output_tokens=request.max_output_tokens,
        )
        return OpenAIResponse(answer=answer, source_documents=context_documents)

    except Exception as e:
        logger.error("RAG pipeline failed", extra={"error": str(e), "query": request.query})
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {str(e)}")


@traceable(name="rag_pipeline_stream")
@router.post("/stream")
async def ask_stream(
    request: OpenAIRequest,
    embedder=Depends(get_embedder),
    retriever: QdrantRetriever = Depends(get_retriever),
    openai_service: OpenAIService = Depends(get_openai_service),
):
    try:
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

                async for chunk in openai_service.generate_stream_response(
                    query=request.query,
                    context_documents=context_documents,
                    model=request.model,
                    temperature=request.temperature,
                    max_output_tokens=request.max_output_tokens,
                ):
                    yield f"data: {chunk}\n\n"

                yield f"data: {json.dumps({'type': 'stream_completed'})}\n\n"

            except Exception as e:
                logger.error("Stream generation failed", extra={"error": str(e)})
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    except Exception as e:
        logger.error("Stream setup failed", extra={"error": str(e), "query": request.query})
        raise HTTPException(status_code=500, detail=f"Failed to start stream: {str(e)}")
