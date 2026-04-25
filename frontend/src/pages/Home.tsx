import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchLessons } from '../api';
import type { Lesson } from '../types';
import TopBar from '../components/TopBar';

// Group an array of lessons by a string key derived from each item.
function groupBy<T>(items: T[], key: (item: T) => string): Record<string, T[]> {
  return items.reduce<Record<string, T[]>>((acc, item) => {
    const k = key(item);
    (acc[k] ??= []).push(item);
    return acc;
  }, {});
}

function LoadingSpinner() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-24">
      <div className="w-10 h-10 rounded-full border-2 border-slate-600 border-t-sky-400 animate-spin" />
      <p className="text-slate-400 text-sm">Carregando aulas…</p>
    </div>
  );
}

function SummaryBadge({ hasSummary }: { hasSummary: boolean }) {
  if (hasSummary) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-900/50 text-emerald-400 border border-emerald-700/50">
        Resumido ✓
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-900/40 text-amber-400 border border-amber-700/40">
      Pendente
    </span>
  );
}

interface LessonCardProps {
  lesson: Lesson;
  onClick: () => void;
}

function LessonCard({ lesson, onClick }: LessonCardProps) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left p-4 rounded-lg bg-slate-800 border border-slate-700 hover:border-sky-400/60 hover:bg-slate-700/70 transition-all group"
    >
      {/* Course badge */}
      {lesson.course && (
        <span className="inline-block mb-2 px-2 py-0.5 rounded text-xs text-sky-400 bg-sky-900/40 border border-sky-700/40 font-medium">
          {lesson.course}
        </span>
      )}

      {/* Title */}
      <p className="text-slate-100 font-semibold text-sm group-hover:text-white transition-colors">
        Aula {lesson.aula_number ?? '—'} — {lesson.topic ?? 'Sem tópico'}
      </p>

      {/* Footer row */}
      <div className="mt-3 flex items-center justify-between">
        <SummaryBadge hasSummary={lesson.summary !== null} />
      </div>
    </button>
  );
}

export default function Home() {
  const navigate = useNavigate();
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchLessons()
      .then(setLessons)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Erro ao carregar aulas');
      })
      .finally(() => setLoading(false));
  }, []);

  const totalCount = lessons.length;
  const summarizedCount = lessons.filter((l) => l.summary !== null).length;

  // Group: course → topic → lessons[]
  const byCourse = groupBy(lessons, (l) => l.course ?? 'Sem curso');

  return (
    <div className="min-h-screen bg-slate-900">
      <TopBar completedCount={summarizedCount} totalCount={totalCount} />

      {/* Page content offset for fixed TopBar (h-13 = 3.25rem) */}
      <main className="pt-13 px-6 pb-12 max-w-5xl mx-auto">
        <div className="mt-8 mb-6">
          <h1 className="text-2xl font-bold text-slate-100">Minhas Aulas</h1>
          <p className="mt-1 text-slate-400 text-sm">
            {summarizedCount} de {totalCount} aulas resumidas
          </p>
        </div>

        {loading && <LoadingSpinner />}

        {error && (
          <div className="p-4 rounded-lg border border-red-700/50 bg-red-900/20 text-red-400 text-sm">
            {error}
          </div>
        )}

        {!loading && !error && lessons.length === 0 && (
          <p className="text-slate-400 text-sm">Nenhuma aula encontrada.</p>
        )}

        {!loading && !error && Object.entries(byCourse).map(([courseName, courseLessons]) => {
          const byTopic = groupBy(courseLessons, (l) => l.topic ?? 'Sem tópico');

          return (
            <section key={courseName} className="mb-10">
              {/* Course heading */}
              <h2 className="text-lg font-bold text-slate-100 mb-4 flex items-center gap-3">
                <span>{courseName}</span>
                <span className="text-slate-500 text-sm font-normal">
                  {courseLessons.length} aulas
                </span>
              </h2>

              {Object.entries(byTopic).map(([topicName, topicLessons]) => {
                const sorted = [...topicLessons].sort(
                  (a, b) => (a.aula_number ?? 0) - (b.aula_number ?? 0),
                );

                return (
                  <div key={topicName} className="mb-6">
                    {/* Topic sub-heading */}
                    <h3 className="text-xs font-semibold uppercase tracking-widest text-sky-400 mb-3 pl-0.5">
                      {topicName}
                    </h3>

                    {/* Lesson cards grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                      {sorted.map((lesson) => (
                        <LessonCard
                          key={lesson.id}
                          lesson={lesson}
                          onClick={() => navigate(`/lesson/${lesson.id}`)}
                        />
                      ))}
                    </div>
                  </div>
                );
              })}
            </section>
          );
        })}
      </main>
    </div>
  );
}
