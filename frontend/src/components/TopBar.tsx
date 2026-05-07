import { Link } from 'react-router-dom';

interface TopBarProps {
  courseName?: string;
  topicName?: string;
  completedCount: number;
  totalCount: number;
}

export default function TopBar({
  courseName,
  topicName,
  completedCount,
  totalCount,
}: TopBarProps) {
  const progress = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;

  return (
    <header className="fixed top-0 left-0 right-0 h-13 z-50 bg-slate-800 border-b border-slate-700 flex items-center px-4 gap-4">
      {/* Logo */}
      <Link to="/" className="text-sky-400 font-bold text-lg shrink-0 hover:text-sky-300 transition-colors">
        Assistente IA
      </Link>

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

      </div>
    </header>
  );
}
