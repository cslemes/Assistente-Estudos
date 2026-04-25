from pydantic import BaseModel, Field
from typing import List, Optional
from app.models.embeddings import Document


class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 5
    topic: Optional[str] = None
    course: Optional[str] = None


class SearchResponse(BaseModel):
    results: List[Document]


class OpenAIRequest(BaseModel):
    query: str
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = None
    limit: Optional[int] = 10
    topic: Optional[str] = None
    course: Optional[str] = None


class OpenAIResponse(BaseModel):
    answer: str
    source_documents: List[Document]


class FlashcardRequest(BaseModel):
    topic: Optional[str] = None
    course: Optional[str] = None
    aula_number: Optional[int] = None
    num_cards: int = Field(default=20, ge=1, le=100)
    deck_name: Optional[str] = None


class TranscribeRequest(BaseModel):
    file_path: str


class ScrapeDownloadRequest(BaseModel):
    url: str
    topic_path: str
    prefix: str = "Activity"


class UploadYoutubeRequest(BaseModel):
    file_path: str
    title: str
    description: str = ""


class ExtractAudioRequest(BaseModel):
    file_path: str


class ExtractAudioBatchRequest(BaseModel):
    folder: str
    recursive: bool = False


class ExtractFramesRequest(BaseModel):
    file_path: str
    interval: int = 5  # seconds between frames


class ExtractFramesBatchRequest(BaseModel):
    folder: str
    interval: int = 5
    recursive: bool = False


class ClassifyFramesRequest(BaseModel):
    frames_dir: str


class ClassifyFramesBatchRequest(BaseModel):
    folder: str
    recursive: bool = False


class SummarizeResponse(BaseModel):
    id: int
    file_path: str
    summary: str
    chunks_processed: int


class IngestSlidesRequest(BaseModel):
    pptx_path: str
    video_path: str
    frames_dir: str
    interval: int = 5


class IngestNotebookRequest(BaseModel):
    ipynb_path: str
    video_path: str
    frames_dir: str
    interval: int = 5


class IngestWhiteboardRequest(BaseModel):
    video_path: str
    frames_dir: str
    interval: int = 5


class Highlight(BaseModel):
    title: str
    description: str
    start_time: int
    video_url: str | None = None


class HighlightsResponse(BaseModel):
    id: int
    file_path: str
    highlights: list[Highlight]
