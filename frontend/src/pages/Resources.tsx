import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { downloadFlashcards, fetchLessons, generateSummary } from '../api';
import TopBar from '../components/TopBar';
import type { Lesson } from '../types';

function LoadingSpinner() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-24">
      <div className="w-8 h-8 rounded-full border-2 border-slate-600 border-t-sky-400 animate-spin" />
    </div>
  );
}

export default function Resources() {
  const { id } = useParams<{ id: string }>();
  const lessonId = parseInt(id!);

  const [lesson, setLesson] = useState<Lesson | undefined>(undefined);
  const [summary, setSummary] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [numCards, setNumCards] = useState(20);
  const [deckName, setDeckName] = useState('');
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    fetchLessons()
      .then((all) => {
        const found = all.find((l) => l.id === lessonId);
        setLesson(found);
        setSummary(found?.summary ?? null);
      })
      .catch(console.error);
  }, [lessonId]);

  async function handleGenerateSummary() {
    setGenerating(true);
    try {
      const result = await generateSummary(lessonId);
      setSummary(result.summary);
    } catch (err) {
      console.error(err);
    } finally {
      setGenerating(false);
    }
  }

  async function handleDownloadFlashcards() {
    setDownloading(true);
    try {
      const blob = await downloadFlashcards({
        course: lesson?.course ?? undefined,
        topic: lesson?.topic ?? undefined,
        aula_number: lesson?.aula_number ?? undefined,
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
      console.error(err);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-900">
      <TopBar
        completedCount={0}
        totalCount={0}
        courseName={lesson?.course ?? undefined}
        topicName={lesson?.topic ?? undefined}
      />

      <main className="pt-[52px]">
        <div className="max-w-2xl mx-auto px-6 py-8">
          {/* Back link */}
          <Link
            to={`/lesson/${lessonId}`}
            className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-sky-400 transition-colors"
          >
            ← Voltar para a aula
          </Link>

          {/* Resumo section */}
          <section className="mt-8">
            <h2 className="text-lg font-bold text-slate-100 mb-4">📋 Resumo da Aula</h2>

            {summary ? (
              <div className="bg-slate-800 rounded-lg p-4 text-sm text-slate-200 leading-relaxed whitespace-pre-wrap border border-slate-700">
                {summary}
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                <p className="text-slate-500 text-sm">Nenhum resumo disponível.</p>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => void handleGenerateSummary()}
                    disabled={generating}
                    className="px-4 py-2 rounded-md bg-sky-500 hover:bg-sky-400 disabled:bg-slate-700 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
                  >
                    Gerar Resumo
                  </button>
                  {generating && (
                    <div className="w-5 h-5 rounded-full border-2 border-slate-600 border-t-sky-400 animate-spin" />
                  )}
                </div>
              </div>
            )}
          </section>

          {/* Flashcards section */}
          <section className="mt-10">
            <h2 className="text-lg font-bold text-slate-100 mb-4">🃏 Flashcards (Anki)</h2>

            <div className="flex flex-col gap-5 bg-slate-800 rounded-lg p-5 border border-slate-700">
              {/* Num cards slider */}
              <div className="flex flex-col gap-2">
                <label className="text-sm text-slate-300 font-medium">
                  Número de cartões:{' '}
                  <span className="text-sky-400 font-bold">{numCards} cartões</span>
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

              {/* Deck name input */}
              <div className="flex flex-col gap-1.5">
                <label className="text-sm text-slate-300 font-medium">
                  Nome do deck
                </label>
                <input
                  type="text"
                  placeholder="Nome do deck (opcional)"
                  value={deckName}
                  onChange={(e) => setDeckName(e.target.value)}
                  className="bg-slate-900 border border-slate-700 focus:border-sky-400 rounded-md px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors"
                />
              </div>

              {/* Download button */}
              <button
                onClick={() => void handleDownloadFlashcards()}
                disabled={downloading || !lesson}
                className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-md bg-sky-500 hover:bg-sky-400 disabled:bg-slate-700 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
              >
                {downloading ? (
                  <>
                    <div className="w-4 h-4 rounded-full border-2 border-white/40 border-t-white animate-spin" />
                    Gerando deck…
                  </>
                ) : (
                  <>⬇ Baixar .apkg</>
                )}
              </button>
            </div>
          </section>

          {/* Show spinner while loading lesson */}
          {!lesson && <LoadingSpinner />}
        </div>
      </main>
    </div>
  );
}
