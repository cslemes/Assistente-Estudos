import { useState } from 'react';
import { downloadFlashcards } from '../api';
import type { Lesson } from '../types';

interface FlashcardsTabProps {
  lesson: Lesson;
}

export default function FlashcardsTab({ lesson }: FlashcardsTabProps) {
  const [numCards, setNumCards] = useState(20);
  const [deckName, setDeckName] = useState('');
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDownload() {
    setDownloading(true);
    setError(null);
    try {
      const blob = await downloadFlashcards({
        course: lesson.course ?? undefined,
        topic: lesson.topic ?? undefined,
        aula_number: lesson.aula_number ?? undefined,
        num_cards: numCards,
        deck_name: deckName || undefined,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${deckName || 'flashcards'}.apkg`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao gerar flashcards');
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="py-4 flex flex-col gap-5 max-w-lg">
      <p className="text-sm text-slate-400 leading-relaxed">
        Gera um deck Anki (.apkg) com flashcards extraídos do conteúdo desta aula.
      </p>

      <div className="flex flex-col gap-5 bg-slate-800 rounded-lg p-5 border border-slate-700">
        {/* Num cards slider */}
        <div className="flex flex-col gap-2">
          <label className="text-sm text-slate-300 font-medium">
            Número de cartões:{' '}
            <span className="text-sky-400 font-bold">{numCards}</span>
          </label>
          <input
            type="range"
            min={5}
            max={50}
            value={numCards}
            onChange={(e) => setNumCards(parseInt(e.target.value))}
            className="w-full accent-sky-400"
          />
          <div className="flex justify-between text-xs text-slate-500">
            <span>5</span>
            <span>50</span>
          </div>
        </div>

        {/* Deck name */}
        <div className="flex flex-col gap-1.5">
          <label className="text-sm text-slate-300 font-medium">Nome do deck</label>
          <input
            type="text"
            placeholder="Nome do deck (opcional)"
            value={deckName}
            onChange={(e) => setDeckName(e.target.value)}
            className="bg-slate-900 border border-slate-700 focus:border-sky-400 rounded-md px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors"
          />
        </div>

        {error && (
          <p className="text-xs text-red-400 bg-red-900/20 border border-red-700/40 rounded px-3 py-2">
            {error}
          </p>
        )}

        <button
          onClick={() => void handleDownload()}
          disabled={downloading}
          className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-md bg-sky-500 hover:bg-sky-400 disabled:bg-slate-700 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
        >
          {downloading ? (
            <>
              <div className="w-4 h-4 rounded-full border-2 border-white/40 border-t-white animate-spin" />
              Gerando deck…
            </>
          ) : (
            '⬇ Baixar .apkg'
          )}
        </button>
      </div>
    </div>
  );
}
