import type { Document } from '../types';
import { formatTime } from '../utils';

interface SourceChipProps {
  document: Document;
}

export default function SourceChip({ document }: SourceChipProps) {
  const { metadata } = document;

  function handleClick() {
    if (metadata.video_url) {
      window.open(metadata.video_url, '_blank', 'noopener,noreferrer');
    }
  }

  const hasLink = Boolean(metadata.video_url);

  return (
    <button
      onClick={handleClick}
      disabled={!hasLink}
      className="inline-flex items-center gap-1.5 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs cursor-pointer hover:border-sky-400 hover:text-sky-400 transition-colors disabled:cursor-default disabled:hover:border-slate-700 disabled:hover:text-inherit"
    >
      <span className="text-sky-400 font-mono">
        {formatTime(metadata.start_time ?? 0)}
      </span>
      {(metadata.course || metadata.aula_number != null) && (
        <span className="text-slate-400">
          {metadata.course}
          {metadata.course && metadata.aula_number != null ? ' · ' : ''}
          {metadata.aula_number != null ? `Aula ${metadata.aula_number}` : ''}
        </span>
      )}
    </button>
  );
}
