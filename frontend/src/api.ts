import type {
  AskStreamEvent,
  FlashcardRequest,
  HighlightsResponse,
  Lesson,
  Segment,
  SummarizeResponse,
} from './types';

export async function fetchLessons(): Promise<Lesson[]> {
  const res = await fetch('/api/summarize');
  if (!res.ok) throw new Error(`fetchLessons failed: ${res.status}`);
  return res.json() as Promise<Lesson[]>;
}

export async function fetchSegments(id: number): Promise<Segment[]> {
  const res = await fetch(`/api/transcriptions/${id}/segments`);
  if (!res.ok) throw new Error(`fetchSegments failed: ${res.status}`);
  return res.json() as Promise<Segment[]>;
}

export async function fetchHighlights(id: number): Promise<HighlightsResponse> {
  const res = await fetch(`/api/highlights/${id}`);
  if (!res.ok) throw new Error(`fetchHighlights failed: ${res.status}`);
  return res.json() as Promise<HighlightsResponse>;
}

export async function generateHighlights(id: number, n?: number): Promise<HighlightsResponse> {
  const url = n !== undefined ? `/api/highlights/${id}?n=${n}` : `/api/highlights/${id}`;
  const res = await fetch(url, { method: 'POST' });
  if (!res.ok) throw new Error(`generateHighlights failed: ${res.status}`);
  return res.json() as Promise<HighlightsResponse>;
}

export async function generateSummary(id: number): Promise<SummarizeResponse> {
  const res = await fetch(`/api/summarize/${id}`, { method: 'POST' });
  if (!res.ok) throw new Error(`generateSummary failed: ${res.status}`);
  return res.json() as Promise<SummarizeResponse>;
}

export async function downloadFlashcards(req: FlashcardRequest): Promise<Blob> {
  const res = await fetch('/api/flashcards/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`downloadFlashcards failed: ${res.status}`);
  return res.blob();
}

export async function* streamAsk(
  query: string,
  course?: string,
  topic?: string,
): AsyncGenerator<AskStreamEvent> {
  const res = await fetch('/api/ask/groq/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, course, topic }),
  });

  if (!res.ok) throw new Error(`streamAsk failed: ${res.status}`);
  if (!res.body) throw new Error('streamAsk: no response body');

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        // Flush remaining buffer after stream closes
        if (buffer.trim()) {
          for (const line of buffer.split('\n').filter((l) => l.startsWith('data: '))) {
            const json = line.slice(6);
            if (json.trim()) {
              yield JSON.parse(json) as AskStreamEvent;
            }
          }
        }
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // SSE messages are separated by \n\n
      const parts = buffer.split('\n\n');
      // Keep the last (potentially incomplete) part in the buffer
      buffer = parts.pop() ?? '';

      for (const part of parts) {
        // Extract the data line from the SSE block
        const dataLine = part
          .split('\n')
          .find((line) => line.startsWith('data: '));
        if (!dataLine) continue;

        const json = dataLine.slice('data: '.length).trim();
        if (!json) continue;

        let event: AskStreamEvent;
        try {
          event = JSON.parse(json) as AskStreamEvent;
        } catch {
          continue;
        }

        yield event;

        if (event.type === 'stream_completed' || event.type === 'error') {
          return;
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
