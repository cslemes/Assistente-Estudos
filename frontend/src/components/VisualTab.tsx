import { useEffect, useState } from 'react';
import { fetchVisualChunks } from '../api';
import { formatTime } from '../utils';
import type { VisualChunk } from '../types';

interface Props {
  lessonId: number;
  onSeek: (seconds: number) => void;
}

const TYPE_STYLES: Record<string, string> = {
  slide:      'bg-sky-900/40 text-sky-400 border-sky-700',
  notebook:   'bg-amber-900/40 text-amber-400 border-amber-700',
  whiteboard: 'bg-emerald-900/40 text-emerald-400 border-emerald-700',
};

const TYPE_BADGE: Record<string, string> = {
  slide:      'bg-sky-500/20 text-sky-400',
  notebook:   'bg-amber-500/20 text-amber-400',
  whiteboard: 'bg-emerald-500/20 text-emerald-400',
};

export default function VisualTab({ lessonId, onSeek }: Props) {
  const [chunks, setChunks] = useState<VisualChunk[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchVisualChunks(lessonId)
      .then(setChunks)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Erro'))
      .finally(() => setLoading(false));
  }, [lessonId]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-8 text-slate-400 text-sm">
        <div className="w-4 h-4 rounded-full border-2 border-slate-600 border-t-sky-400 animate-spin" />
        Carregando conteúdo visual…
      </div>
    );
  }

  if (error) {
    return <p className="text-red-400 text-sm py-4">{error}</p>;
  }

  if (chunks.length === 0) {
    return (
      <p className="text-slate-500 text-sm py-8">
        Nenhum conteúdo visual disponível. Execute o pipeline de visão para esta aula.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3 py-4">
      {chunks.map((chunk, i) => (
        <button
          key={i}
          onClick={() => chunk.start_time != null && onSeek(chunk.start_time)}
          className={`w-full text-left p-3 rounded-lg border transition-colors hover:brightness-110 ${TYPE_STYLES[chunk.source_type] ?? 'bg-slate-800 border-slate-700 text-slate-300'}`}
        >
          <div className="flex items-center gap-2 mb-1.5">
            <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${TYPE_BADGE[chunk.source_type] ?? ''}`}>
              {chunk.source_type}
            </span>
            {chunk.start_time != null && (
              <span className="text-xs font-mono text-slate-400">
                {formatTime(chunk.start_time)}
              </span>
            )}
          </div>
          {chunk.source_type === 'notebook' ? (
            <pre className="text-xs text-amber-300 font-mono whitespace-pre-wrap break-words leading-relaxed">
              {chunk.text}
            </pre>
          ) : (
            <p className={`text-sm leading-relaxed ${chunk.source_type === 'whiteboard' ? 'italic' : ''}`}>
              {chunk.text}
            </p>
          )}
        </button>
      ))}
    </div>
  );
}
