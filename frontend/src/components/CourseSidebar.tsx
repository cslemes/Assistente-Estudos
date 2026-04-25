import type { Lesson } from '../types';

interface CourseSidebarProps {
  lessons: Lesson[];
  currentId: number;
  onSelect: (id: number) => void;
}

function StatusIcon({ done, current }: { done: boolean; current: boolean }) {
  if (current) {
    return <span className="text-sky-400 text-sm w-4 shrink-0">●</span>;
  }
  if (done) {
    return <span className="text-emerald-400 text-sm w-4 shrink-0">✓</span>;
  }
  return <span className="text-slate-500 text-sm w-4 shrink-0">○</span>;
}

export default function CourseSidebar({ lessons, currentId, onSelect }: CourseSidebarProps) {
  // Group by topic, preserve insertion order
  const byTopic = lessons.reduce<Record<string, Lesson[]>>((acc, l) => {
    const key = l.topic ?? 'Sem tópico';
    (acc[key] ??= []).push(l);
    return acc;
  }, {});

  // Sort lessons within each topic by aula_number
  Object.values(byTopic).forEach((group) =>
    group.sort((a, b) => (a.aula_number ?? 0) - (b.aula_number ?? 0)),
  );

  return (
    <aside className="w-full h-full flex flex-col bg-slate-800 overflow-y-auto">
      <div className="px-4 py-3 border-b border-slate-700 shrink-0">
        <h2 className="text-slate-100 font-semibold text-sm uppercase tracking-wide">
          Conteúdo do Curso
        </h2>
      </div>

      <nav className="flex-1 py-2">
        {Object.entries(byTopic).map(([topicName, topicLessons]) => (
          <div key={topicName}>
            {/* Topic header */}
            <div className="px-4 pt-4 pb-1">
              <p className="text-xs font-semibold uppercase tracking-widest text-sky-500">
                {topicName}
              </p>
            </div>

            {/* Lessons under this topic */}
            {topicLessons.map((lesson) => {
              const isCurrent = lesson.id === currentId;
              const isDone = lesson.summary !== null;

              return (
                <button
                  key={lesson.id}
                  onClick={() => onSelect(lesson.id)}
                  className={[
                    'w-full flex items-start gap-2.5 px-4 py-2.5 text-left transition-colors',
                    'hover:bg-slate-700',
                    isCurrent
                      ? 'border-l-2 border-sky-400 bg-slate-700/60 pl-3.5'
                      : 'border-l-2 border-transparent',
                  ].join(' ')}
                >
                  <StatusIcon done={isDone} current={isCurrent} />

                  <div className="flex-1 min-w-0">
                    <p
                      className={[
                        'text-sm font-medium truncate',
                        isCurrent ? 'text-sky-400' : isDone ? 'text-slate-300' : 'text-slate-400',
                      ].join(' ')}
                    >
                      {lesson.aula_number != null ? `Aula ${lesson.aula_number}` : 'Aula —'}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}
