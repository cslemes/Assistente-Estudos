import { Link } from 'react-router-dom';

interface TopBarProps {
  courseName?: string;
  topicName?: string;
  completedCount: number;
  totalCount: number;
  lessonId?: number;
}

export default function TopBar({
  courseName,
  topicName,
  completedCount,
  totalCount,
  lessonId,
}: TopBarProps) {
  const progress = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;

  return (
    <header className="fixed top-0 left-0 right-0 h-13 z-50 bg-slate-800 border-b border-slate-700 flex items-center px-4 gap-4">
      {/* Logo */}
      <span className="text-sky-400 font-bold text-lg shrink-0">Assistente IA</span>

      {/* Breadcrumb */}
      <div className="flex-1 flex justify-center">
        {courseName && topicName && (
          <span className="text-slate-400 text-sm truncate">
            {courseName}
            <span className="mx-1.5">›</span>
            {topicName}
          </span>
        )}
      </div>

      {/* Right side: progress + recursos */}
      <div className="flex items-center gap-3 shrink-0">
        {/* Progress bar + label */}
        <div className="flex items-center gap-2">
          <div className="w-28 h-2 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-sky-500 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="text-slate-400 text-xs whitespace-nowrap">
            {completedCount}/{totalCount} aulas
          </span>
        </div>

        {/* Recursos button */}
        {lessonId !== undefined && (
          <Link
            to={`/lesson/${lessonId}/resources`}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-slate-700 hover:bg-slate-600 border border-slate-600 hover:border-sky-400 text-slate-100 text-sm transition-colors"
          >
            <span>📚</span>
            <span>Recursos</span>
          </Link>
        )}
      </div>
    </header>
  );
}
