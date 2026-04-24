// Lesson — from GET /summarize
export interface Lesson {
  id: number;
  file_path: string;
  video_url: string | null;
  status: string;
  summary: string | null;
  created_at: string;
  course: string | null;
  topic: string | null;
  aula_number: number | null;
}

// Segment — from GET /transcriptions/{id}/segments
export interface Segment {
  text: string;
  start: number;
  end: number;
  speaker: number | null;
}

// Highlight — individual highlight item
export interface Highlight {
  title: string;
  description: string;
  start_time: number;
  video_url: string;
}

// HighlightsResponse — from GET /highlights/{id} and POST /highlights/{id}
export interface HighlightsResponse {
  id: number;
  file_path: string;
  highlights: Highlight[];
}

// DocumentMetadata — nested inside Document
export interface DocumentMetadata {
  course: string | null;
  topic: string | null;
  aula_number: number | null;
  video_url: string | null;
  source_type: string;
  start_time: number | null;
  transcription_id: number | null;
}

// Document — used in source_documents SSE event
export interface Document {
  page_content: string;
  metadata: DocumentMetadata;
}

// Discriminated union for SSE events from POST /ask/stream
export interface SourceDocumentsEvent {
  type: 'source_documents';
  documents: Document[];
}

export interface TextDeltaEvent {
  type: 'text_delta';
  text: string;
}

export interface StreamCompletedEvent {
  type: 'stream_completed';
}

export interface ErrorEvent {
  type: 'error';
  message: string;
}

export type AskStreamEvent =
  | SourceDocumentsEvent
  | TextDeltaEvent
  | StreamCompletedEvent
  | ErrorEvent;

// SummarizeResponse — from POST /summarize/{id}
export interface SummarizeResponse {
  id: number;
  file_path: string;
  summary: string;
  chunks_processed: number;
}

// FlashcardRequest — body for POST /flashcards/generate
export interface FlashcardRequest {
  topic?: string;
  course?: string;
  aula_number?: number;
  num_cards?: number;
  deck_name?: string;
}
