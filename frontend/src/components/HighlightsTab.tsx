import { useEffect, useState } from 'react';
import { fetchHighlights, generateHighlights } from '../api';
import type { Highlight } from '../types';
import { formatTime } from '../utils';

interface HighlightsTabProps {
  lessonId: number;
  onSeek: (seconds: number) => void;
}

function LoadingSpinner({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12">
      <div className="w-8 h-8 rounded-full border-2 border-slate-600 border-t-sky-400 animate-spin" />
      <p className="text-slate-400 text-sm">{label ?? 'Carregando…'}</p>
    </div>
  );
}

export default function HighlightsTab({ lessonId, onSeek }: HighlightsTabProps) {
  const [highlights, setHighlights] = useState<Highlight[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setNotFound(false);

    fetchHighlights(lessonId)
      .then((data) => {
        setHighlights(data.highlights);
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : String(err);
        if (msg.includes('404')) {
          setNotFound(true);
        } else {
          setError(msg);
        }
      })
      .finally(() => setLoading(false));
  }, [lessonId]);

  function handleGenerate() {
    setGenerating(true);
    setError(null);
    generateHighlights(lessonId, 5)
      .then((data) => {
        setHighlights(data.highlights);
        setNotFound(false);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => setGenerating(false));
  }

  if (loading) return <LoadingSpinner label="Carregando highlights…" />;
  if (generating) return <LoadingSpinner label="Gerando highlights…" />;

  if (error) {
    return (
      <div className="p-4 rounded-lg border border-red-700/50 bg-red-900/20 text-red-400 text-sm">
        {error}
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-12">
        <p className="text-slate-400 text-sm">Nenhum highlight disponível para esta aula.</p>
        <button
          onClick={handleGenerate}
          className="px-4 py-2 rounded-md bg-sky-500 hover:bg-sky-400 text-white text-sm font-medium transition-colors"
        >
          Gerar Highlights
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 p-3">
      {highlights.map((hl, idx) => (
        <div
          key={idx}
          className="rounded-lg bg-slate-800 border border-slate-700 p-4 flex flex-col gap-2"
        >
          <p className="text-sky-400 font-semibold text-sm leading-snug">{hl.title}</p>
          <p className="text-slate-300 text-sm leading-relaxed">{hl.description}</p>
          <div className="mt-1">
            <button
              onClick={() => onSeek(hl.start_time)}
              className="inline-flex items-center px-2.5 py-1 rounded border border-sky-500/60 text-sky-400 text-xs font-mono hover:bg-sky-500/10 hover:border-sky-400 transition-colors"
            >
              {formatTime(hl.start_time)}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
