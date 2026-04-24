import { useRef, useEffect, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { useAskStream } from '../hooks/useAskStream';
import SourceChip from './SourceChip';

interface AiChatProps {
  course?: string;
  topic?: string;
}

function StreamingDots() {
  return (
    <span className="inline-flex items-center gap-1 ml-1">
      <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-bounce [animation-delay:-0.3s]" />
      <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-bounce [animation-delay:-0.15s]" />
      <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-bounce" />
    </span>
  );
}

export default function AiChat({ course, topic }: AiChatProps) {
  const { messages, isStreaming, send, clear } = useAskStream();
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    const maxHeight = 4 * 24; // ~4 rows
    el.style.height = `${Math.min(el.scrollHeight, maxHeight)}px`;
  }, [input]);

  async function handleSend() {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    setInput('');
    await send(trimmed, course, topic);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  }

  return (
    <div className="flex flex-col h-full bg-slate-800">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-700 shrink-0">
        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-sky-400 to-indigo-500 flex items-center justify-center shrink-0">
          <svg
            className="w-5 h-5 text-white"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.5}
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
            />
          </svg>
        </div>
        <div className="min-w-0">
          <p className="text-slate-100 text-sm font-semibold leading-tight">Assistente</p>
          <p className="text-slate-400 text-xs leading-tight truncate">Pergunte sobre esta aula</p>
        </div>
        {messages.length > 0 && (
          <button
            onClick={clear}
            className="ml-auto text-slate-500 hover:text-slate-300 transition-colors text-xs"
            title="Limpar conversa"
          >
            Limpar
          </button>
        )}
      </div>

      {/* Message thread */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
            <p className="text-slate-500 text-sm">
              Faça uma pergunta sobre o conteúdo desta aula.
            </p>
          </div>
        )}

        {messages.map((msg, idx) => {
          const isLast = idx === messages.length - 1;
          return (
            <div key={idx} className="flex flex-col gap-1.5">
              {msg.role === 'user' ? (
                <div className="flex justify-end">
                  <p className="text-sky-400 italic text-sm bg-slate-900/60 border border-slate-700 rounded-lg px-3 py-2 max-w-[85%]">
                    {msg.content}
                  </p>
                </div>
              ) : (
                <div className="flex flex-col gap-2">
                  <div className="text-slate-200 text-sm leading-relaxed">
                    {msg.content}
                    {isLast && isStreaming && <StreamingDots />}
                  </div>

                  {/* Source chips */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {msg.sources.map((doc, docIdx) => (
                        <SourceChip key={docIdx} document={doc} />
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="shrink-0 border-t border-slate-700 p-3">
        <div className="flex items-end gap-2 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 focus-within:border-sky-400 transition-colors">
          <textarea
            ref={textareaRef}
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isStreaming}
            placeholder="Pergunte sobre esta aula…"
            className="flex-1 bg-transparent text-slate-100 text-sm placeholder-slate-500 resize-none outline-none leading-6 disabled:opacity-50"
            style={{ maxHeight: '96px', overflowY: 'auto' }}
          />
          <button
            onClick={() => void handleSend()}
            disabled={isStreaming || !input.trim()}
            className="shrink-0 w-8 h-8 rounded-md bg-sky-500 hover:bg-sky-400 disabled:bg-slate-700 disabled:cursor-not-allowed flex items-center justify-center transition-colors mb-0.5"
            title="Enviar"
          >
            <svg
              className="w-4 h-4 text-white"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" />
            </svg>
          </button>
        </div>
        <p className="text-slate-600 text-xs mt-1.5 px-1">
          Enter para enviar · Shift+Enter para nova linha
        </p>
      </div>
    </div>
  );
}
