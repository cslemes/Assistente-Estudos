import { useEffect, useState } from 'react';
import { fetchSegments } from '../api';
import type { Segment } from '../types';
import { formatTime } from '../utils';

interface TranscriptTabProps {
  lessonId: number;
  onSeek: (seconds: number) => void;
}

function LoadingSpinner() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12">
      <div className="w-8 h-8 rounded-full border-2 border-slate-600 border-t-sky-400 animate-spin" />
      <p className="text-slate-400 text-sm">Carregando transcrição…</p>
    </div>
  );
}

export default function TranscriptTab({ lessonId, onSeek }: TranscriptTabProps) {
  const [segments, setSegments] = useState<Segment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [empty, setEmpty] = useState(false);

  useEffect(() => {
    setSegments([]);
    setLoading(true);
    setError(null);
    setEmpty(false);

    fetchSegments(lessonId)
      .then((data) => {
        if (data.length === 0) {
          setEmpty(true);
        } else {
          setSegments(data);
        }
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : String(err);
        // Treat 404 as "not available" rather than a hard error
        if (msg.includes('404')) {
          setEmpty(true);
        } else {
          setError(msg);
        }
      })
      .finally(() => setLoading(false));
  }, [lessonId]);

  if (loading) return <LoadingSpinner />;

  if (error) {
    return (
      <div className="p-4 rounded-lg border border-red-700/50 bg-red-900/20 text-red-400 text-sm">
        {error}
      </div>
    );
  }

  if (empty) {
    return (
      <div className="py-12 text-center">
        <p className="text-slate-400 text-sm">Transcrição não disponível</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col divide-y divide-slate-700/50 overflow-y-auto">
      {segments.map((seg, idx) => (
        <button
          key={idx}
          onClick={() => onSeek(Math.floor(seg.start))}
          className="flex items-start gap-3 px-3 py-2.5 text-left hover:bg-slate-700/50 transition-colors w-full"
        >
          <span className="shrink-0 text-sky-400 text-xs font-mono pt-0.5 w-10 text-right">
            {formatTime(seg.start)}
          </span>
          <span className="text-slate-300 text-sm leading-relaxed">{seg.text}</span>
        </button>
      ))}
    </div>
  );
}
