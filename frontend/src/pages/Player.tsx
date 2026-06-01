import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { fetchLessons, generateSummary } from '../api';
import AiChat from '../components/AiChat';
import CourseSidebar from '../components/CourseSidebar';
import FlashcardsTab from '../components/FlashcardsTab';
import HighlightsTab from '../components/HighlightsTab';
import TopBar from '../components/TopBar';
import TranscriptTab from '../components/TranscriptTab';
import VideoPlayer from '../components/VideoPlayer';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Lesson } from '../types';

type ActiveTab = 'transcript' | 'highlights' | 'flashcards' | 'resumo';

function LoadingSpinner() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 h-screen bg-slate-900">
      <div className="w-10 h-10 rounded-full border-2 border-slate-600 border-t-sky-400 animate-spin" />
      <p className="text-slate-400 text-sm">Carregando aulas…</p>
    </div>
  );
}

export default function Player() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const currentId = parseInt(id!);

  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);
  const [seekTo, setSeekTo] = useState<number | undefined>(undefined);
  const [activeTab, setActiveTab] = useState<ActiveTab>('transcript');
  const [summary, setSummary] = useState<string | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  useEffect(() => {
    fetchLessons().then(setLessons).catch(console.error).finally(() => setLoading(false));
  }, []);

  // Reset per-lesson state and load summary when lesson changes
  useEffect(() => {
    setSeekTo(undefined);
    setActiveTab('transcript');
    setSummaryError(null);
    const lesson = lessons.find((l) => l.id === currentId);
    setSummary(lesson?.summary ?? null);
  }, [currentId, lessons]);

  if (loading) return <LoadingSpinner />;

  const currentLesson = lessons.find((l) => l.id === currentId);

  if (!currentLesson) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-900 text-slate-400">
        Aula não encontrada.
      </div>
    );
  }

  const sidebarLessons = lessons.filter((l) => l.course === currentLesson.course);

  const completedCount = sidebarLessons.filter((l) => l.summary !== null).length;

  return (
    <div className="bg-slate-900 min-h-screen">
      {/* Fixed TopBar */}
      <TopBar
        courseName={currentLesson.course ?? undefined}
        topicName={currentLesson.topic ?? undefined}
        completedCount={completedCount}
        totalCount={sidebarLessons.length}
      />

      {/* 3-column layout below TopBar */}
      <div
        className="fixed left-0 right-0 flex"
        style={{ top: '52px', height: 'calc(100vh - 52px)' }}
      >
        {/* Left panel — sidebar */}
        <div className="w-[280px] shrink-0 h-full overflow-y-auto border-r border-slate-700">
          <CourseSidebar
            lessons={sidebarLessons}
            currentId={currentId}
            onSelect={(newId) => navigate('/lesson/' + newId)}
          />
        </div>

        {/* Center panel */}
        <div className="flex-1 h-full overflow-y-auto flex flex-col">
          {/* Video */}
          <div className="p-4">
            <VideoPlayer videoUrl={currentLesson.video_url ?? ''} seekTo={seekTo} />

            {/* Title + breadcrumb */}
            <div className="mt-3">
              <h1 className="text-xl font-bold text-slate-100">
                Aula {currentLesson.aula_number ?? '—'} — {currentLesson.topic ?? 'Sem tópico'}
              </h1>
              <p className="text-sm text-slate-400 mt-1">
                {currentLesson.course ?? ''}
                {currentLesson.course && currentLesson.topic ? ' › ' : ''}
                {currentLesson.topic ?? ''}
                {currentLesson.aula_number != null
                  ? ` · Aula ${currentLesson.aula_number}`
                  : ''}
              </p>
            </div>

            {/* Tab bar */}
            <div className="flex gap-0 mt-4 border-b border-slate-700">
              <button
                onClick={() => setActiveTab('transcript')}
                className={[
                  'px-4 py-2 text-sm font-medium transition-colors',
                  activeTab === 'transcript'
                    ? 'border-b-2 border-sky-400 text-sky-400'
                    : 'text-slate-400 hover:text-slate-200',
                ].join(' ')}
              >
                Transcrição
              </button>
              <button
                onClick={() => setActiveTab('highlights')}
                className={[
                  'px-4 py-2 text-sm font-medium transition-colors',
                  activeTab === 'highlights'
                    ? 'border-b-2 border-sky-400 text-sky-400'
                    : 'text-slate-400 hover:text-slate-200',
                ].join(' ')}
              >
                Highlights
              </button>
              <button
                onClick={() => setActiveTab('flashcards')}
                className={[
                  'px-4 py-2 text-sm font-medium transition-colors',
                  activeTab === 'flashcards'
                    ? 'border-b-2 border-sky-400 text-sky-400'
                    : 'text-slate-400 hover:text-slate-200',
                ].join(' ')}
              >
                Flashcards
              </button>
              <button
                onClick={() => setActiveTab('resumo')}
                className={[
                  'px-4 py-2 text-sm font-medium transition-colors',
                  activeTab === 'resumo'
                    ? 'border-b-2 border-sky-400 text-sky-400'
                    : 'text-slate-400 hover:text-slate-200',
                ].join(' ')}
              >
                Resumo
              </button>
            </div>
          </div>

          {/* Tab content */}
          <div className="flex-1 px-4 pb-4">
            {activeTab === 'transcript' && (
              <TranscriptTab lessonId={currentId} onSeek={setSeekTo} />
            )}
            {activeTab === 'highlights' && (
              <HighlightsTab lessonId={currentId} onSeek={setSeekTo} />
            )}
            {activeTab === 'flashcards' && (
              <FlashcardsTab lesson={currentLesson} />
            )}
            {activeTab === 'resumo' && (
              <div className="py-4">
                {summary ? (
                  <div className="prose prose-invert prose-sm max-w-none prose-headings:text-slate-100 prose-p:text-slate-300 prose-strong:text-slate-100 prose-li:text-slate-300">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{summary}</ReactMarkdown>
                  </div>
                ) : (
                  <div className="flex flex-col items-start gap-4">
                    <p className="text-slate-400 text-sm">Nenhum resumo disponível para esta aula.</p>
                    {summaryError && (
                      <p className="text-red-400 text-sm">{summaryError}</p>
                    )}
                    <button
                      disabled={summaryLoading}
                      onClick={async () => {
                        setSummaryLoading(true);
                        setSummaryError(null);
                        try {
                          const res = await generateSummary(currentId);
                          setSummary(res.summary);
                        } catch (e) {
                          setSummaryError(e instanceof Error ? e.message : 'Erro ao gerar resumo');
                        } finally {
                          setSummaryLoading(false);
                        }
                      }}
                      className="px-4 py-2 bg-sky-500 hover:bg-sky-400 disabled:bg-slate-600 text-white text-sm font-medium rounded-lg transition-colors"
                    >
                      {summaryLoading ? 'Gerando…' : 'Gerar Resumo'}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right panel — AI Chat */}
        <div className="w-[340px] shrink-0 h-full overflow-y-auto border-l border-slate-700">
          <AiChat
            course={currentLesson.course ?? undefined}
            topic={currentLesson.topic ?? undefined}
          />
        </div>
      </div>
    </div>
  );
}
