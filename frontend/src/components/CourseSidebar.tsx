import type { Lesson } from '../types';

interface CourseSidebarProps {
  lessons: Lesson[];
  currentId: number;
  onSelect: (id: number) => void;
}

function StatusIcon({ done, current }: { done: boolean; current: boolean }) {
  if (done) {
    return (
      <span className="text-sky-400 font-bold text-sm w-4 shrink-0" title="Concluído">
        ✓
      </span>
    );
  }
  if (current) {
    return (
      <span className="text-sky-400 text-sm w-4 shrink-0" title="Aula atual">
        ●
      </span>
    );
  }
  return (
    <span className="text-slate-500 text-sm w-4 shrink-0" title="Pendente">
      ○
    </span>
  );
}

export default function CourseSidebar({ lessons, currentId, onSelect }: CourseSidebarProps) {
  const sorted = [...lessons].sort((a, b) => (a.aula_number ?? 0) - (b.aula_number ?? 0));

  return (
    <aside className="w-64 shrink-0 h-full flex flex-col bg-slate-800 border-r border-slate-700 overflow-y-auto">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-700">
        <h2 className="text-slate-100 font-semibold text-sm uppercase tracking-wide">
          Conteúdo do Curso
        </h2>
      </div>

      {/* Lesson list */}
      <nav className="flex-1 py-2">
        {sorted.map((lesson) => {
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
                  Aula {lesson.aula_number ?? '—'}
                </p>
                {lesson.topic && (
                  <p className="text-xs text-slate-500 truncate mt-0.5">{lesson.topic}</p>
                )}
              </div>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
