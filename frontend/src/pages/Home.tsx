import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchLessons } from '../api';
import type { Lesson } from '../types';
import TopBar from '../components/TopBar';
import AiChat from '../components/AiChat';

function groupBy<T>(items: T[], key: (item: T) => string): Record<string, T[]> {
  return items.reduce<Record<string, T[]>>((acc, item) => {
    const k = key(item);
    (acc[k] ??= []).push(item);
    return acc;
  }, {});
}

function firstLessonId(lessons: Lesson[]): number | null {
  const sorted = [...lessons].sort((a, b) => (a.aula_number ?? 0) - (b.aula_number ?? 0));
  return sorted[0]?.id ?? null;
}

function LoadingSpinner() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-24">
      <div className="w-10 h-10 rounded-full border-2 border-slate-600 border-t-sky-400 animate-spin" />
      <p className="text-slate-400 text-sm">Carregando aulas…</p>
    </div>
  );
}

function CourseCard({ name, lessons, onClick }: { name: string; lessons: Lesson[]; onClick: () => void }) {
  const summarized = lessons.filter((l) => l.summary !== null).length;
  const pct = lessons.length > 0 ? Math.round((summarized / lessons.length) * 100) : 0;
  const topics = [...new Set(lessons.map((l) => l.topic ?? 'Sem tópico'))];

  return (
    <button
      onClick={onClick}
      className="w-full text-left p-6 rounded-xl bg-slate-800 border border-slate-700 hover:border-sky-400/60 hover:bg-slate-700/60 transition-all group"
    >
      <h2 className="text-base font-bold text-slate-100 group-hover:text-white leading-snug mb-1">
        {name}
      </h2>
      <p className="text-xs text-slate-500 mb-4">
        {topics.slice(0, 3).join(' · ')}{topics.length > 3 ? ` +${topics.length - 3}` : ''}
      </p>
      <div className="w-full h-1.5 bg-slate-700 rounded-full overflow-hidden mb-2">
        <div className="h-full bg-sky-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
      </div>
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-500">{summarized}/{lessons.length} resumidas</p>
        <span className="text-xs text-sky-400 group-hover:translate-x-0.5 transition-transform">Ver aulas →</span>
      </div>
    </button>
  );
}

type HomeTab = 'courses' | 'chat';

export default function Home() {
  const navigate = useNavigate();
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<HomeTab>('courses');

  useEffect(() => {
    fetchLessons()
      .then(setLessons)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Erro ao carregar aulas'))
      .finally(() => setLoading(false));
  }, []);

  const byCourse = groupBy(lessons, (l) => l.course ?? 'Sem curso');
  const summarizedCount = lessons.filter((l) => l.summary !== null).length;

  return (
    <div className="min-h-screen bg-slate-900">
      <TopBar completedCount={summarizedCount} totalCount={lessons.length} />

      <main className="pt-13 px-6 pb-12 max-w-5xl mx-auto">
        <div className="mt-6 flex gap-1 border-b border-slate-700">
          {(['courses', 'chat'] as HomeTab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
                activeTab === tab
                  ? 'border-sky-400 text-sky-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              {tab === 'courses' ? 'Cursos' : 'Chat'}
            </button>
          ))}
        </div>

        {activeTab === 'courses' && (
          <>
            {loading && <div className="mt-16"><LoadingSpinner /></div>}

            {error && (
              <div className="mt-8 p-4 rounded-lg border border-red-700/50 bg-red-900/20 text-red-400 text-sm">{error}</div>
            )}

            {!loading && !error && (
              <>
                <div className="mt-8 mb-6">
                  <h1 className="text-2xl font-bold text-slate-100">Meus Cursos</h1>
                  <p className="mt-1 text-slate-400 text-sm">
                    {Object.keys(byCourse).length} curso{Object.keys(byCourse).length !== 1 ? 's' : ''} · {summarizedCount} de {lessons.length} aulas resumidas
                  </p>
                </div>
                {lessons.length === 0 && <p className="text-slate-400 text-sm">Nenhum curso encontrado.</p>}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {Object.entries(byCourse).sort(([a], [b]) => a.localeCompare(b)).map(([name, cls]) => {
                    const id = firstLessonId(cls);
                    return (
                      <CourseCard
                        key={name}
                        name={name}
                        lessons={cls}
                        onClick={() => id != null && navigate(`/lesson/${id}`)}
                      />
                    );
                  })}
                </div>
              </>
            )}
          </>
        )}

        {activeTab === 'chat' && (
          <div className="mt-6">
            <AiChat />
          </div>
        )}
      </main>
    </div>
  );
}
