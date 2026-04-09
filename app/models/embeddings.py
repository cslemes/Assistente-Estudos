from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class SparseVector(BaseModel):
    indices: List[int]
    values: List[float]


class QueryEmbeddings(BaseModel):
    dense: List[float]
    sparse_bm25: SparseVector
    late: List[List[float]]


class Document(BaseModel):
    page_content: str
    metadata: Optional[Dict[str, Any]] = None


def format_context(docs: List[Document]) -> str:
    """
    Format retrieved documents into a context string for the LLM,
    including course, topic, and video URL as a header per chunk.
    """
    parts = []
    for doc in docs:
        m = doc.metadata or {}
        label = " — ".join(p for p in [m.get("course"), m.get("topic")] if p) or "Aula"
        url = m.get("video_url", "")
        url_str = f" | {url}" if url else ""
        parts.append(f"[{label}{url_str}]\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)
