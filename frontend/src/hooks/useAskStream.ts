import { useState } from 'react';
import { streamAsk } from '../api';
import type { Document } from '../types';

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: Document[];
}

export interface UseAskStreamReturn {
  messages: Message[];
  isStreaming: boolean;
  send: (query: string, course?: string, topic?: string) => Promise<void>;
  clear: () => void;
}

export function useAskStream(): UseAskStreamReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  async function send(query: string, course?: string, topic?: string): Promise<void> {
    // 1. Append user message
    setMessages((prev) => [...prev, { role: 'user', content: query }]);

    // 2. Start streaming
    setIsStreaming(true);

    // 3. Append empty assistant message
    setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

    try {
      for await (const event of streamAsk(query, course, topic)) {
        if (event.type === 'text_delta') {
          // Append delta text to the last message's content
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            updated[updated.length - 1] = {
              ...last,
              content: last.content + event.text,
            };
            return updated;
          });
        } else if (event.type === 'source_documents') {
          // Set sources on the last message
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            updated[updated.length - 1] = {
              ...last,
              sources: event.documents,
            };
            return updated;
          });
        } else if (event.type === 'stream_completed') {
          break;
        } else if (event.type === 'error') {
          // Append error message to last message content
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            updated[updated.length - 1] = {
              ...last,
              content: last.content + event.message,
            };
            return updated;
          });
          break;
        }
      }
    } finally {
      setIsStreaming(false);
    }
  }

  function clear() {
    setMessages([]);
  }

  return { messages, isStreaming, send, clear };
}
