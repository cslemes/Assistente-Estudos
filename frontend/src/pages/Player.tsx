import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Alert, Button, Spin, Tabs, Typography } from 'antd';
import { FileTextOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { fetchLessons, generateSummary } from '../api';
import AiChat from '../components/AiChat';
import CourseSidebar from '../components/CourseSidebar';
import DocsTab from '../components/DocsTab';
import FlashcardsTab from '../components/FlashcardsTab';
import HighlightsTab from '../components/HighlightsTab';
import TopBar from '../components/TopBar';
import TranscriptTab from '../components/TranscriptTab';
import VideoPlayer from '../components/VideoPlayer';
import type { Lesson } from '../types';

const { Title, Text } = Typography;

export default function Player() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const currentId = parseInt(id!);

  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);
  const [seekTo, setSeekTo] = useState<number | undefined>(undefined);
  const [activeTab, setActiveTab] = useState('transcript');
  const [summary, setSummary] = useState<string | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  useEffect(() => {
    fetchLessons().then(setLessons).catch(console.error).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    setSeekTo(undefined);
    setActiveTab('transcript');
    setSummaryError(null);
    const lesson = lessons.find((l) => l.id === currentId);
    setSummary(lesson?.summary ?? null);
  }, [currentId, lessons]);

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#0f172a', gap: 12 }}>
        <Spin size="large" tip="Carregando aulas…" />
      </div>
    );
  }

  const currentLesson = lessons.find((l) => l.id === currentId);

  if (!currentLesson) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#0f172a' }}>
        <Text style={{ color: '#64748b' }}>Aula não encontrada.</Text>
      </div>
    );
  }

  const sidebarLessons = lessons.filter((l) => l.course === currentLesson.course);
  const completedCount = sidebarLessons.filter((l) => l.summary !== null).length;

  const resumoContent = summary ? (
    <div className="prose prose-invert prose-sm max-w-none prose-headings:text-slate-100 prose-p:text-slate-300 prose-strong:text-slate-100 prose-li:text-slate-300" style={{ paddingTop: 16 }}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{summary}</ReactMarkdown>
    </div>
  ) : (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 12, paddingTop: 16 }}>
      <Text style={{ color: '#64748b', fontSize: 13 }}>Nenhum resumo disponível para esta aula.</Text>
      {summaryError && <Alert type="error" message={summaryError} />}
      <Button
        type="primary"
        icon={<FileTextOutlined />}
        loading={summaryLoading}
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
      >
        {summaryLoading ? 'Gerando…' : 'Gerar Resumo'}
      </Button>
    </div>
  );

  const tabItems = [
    { key: 'transcript', label: 'Transcrição', children: <TranscriptTab lessonId={currentId} onSeek={setSeekTo} /> },
    { key: 'highlights', label: 'Highlights', children: <HighlightsTab lessonId={currentId} onSeek={setSeekTo} /> },
    { key: 'flashcards', label: 'Flashcards', children: <FlashcardsTab lesson={currentLesson} /> },
    { key: 'resumo', label: 'Resumo', children: resumoContent },
    { key: 'docs', label: 'Documentos', children: <DocsTab lessonId={currentId} /> },
  ];

  return (
    <div style={{ background: '#0f172a', minHeight: '100vh' }}>
      <TopBar
        courseName={currentLesson.course ?? undefined}
        topicName={currentLesson.topic ?? undefined}
        completedCount={completedCount}
        totalCount={sidebarLessons.length}
      />

      <div style={{ position: 'fixed', left: 0, right: 0, top: 52, height: 'calc(100vh - 52px)', display: 'flex' }}>
        {/* Sidebar */}
        <div style={{ width: 280, flexShrink: 0, height: '100%', overflowY: 'auto', borderRight: '1px solid #334155' }}>
          <CourseSidebar
            lessons={sidebarLessons}
            currentId={currentId}
            onSelect={(newId) => navigate('/lesson/' + newId)}
          />
        </div>

        {/* Center panel */}
        <div style={{ flex: 1, height: '100%', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: 16 }}>
            <VideoPlayer videoUrl={currentLesson.video_url ?? ''} seekTo={seekTo} lessonId={currentId} />

            <div style={{ marginTop: 12 }}>
              <Title level={4} style={{ color: '#f1f5f9', margin: 0 }}>
                Aula {currentLesson.aula_number ?? '—'} — {currentLesson.topic ?? 'Sem tópico'}
              </Title>
              <Text style={{ color: '#64748b', fontSize: 13 }}>
                {currentLesson.course ?? ''}
                {currentLesson.course && currentLesson.topic ? ' › ' : ''}
                {currentLesson.topic ?? ''}
                {currentLesson.aula_number != null ? ` · Aula ${currentLesson.aula_number}` : ''}
              </Text>
            </div>

            <Tabs
              activeKey={activeTab}
              onChange={setActiveTab}
              items={tabItems}
              style={{ marginTop: 8 }}
            />
          </div>
        </div>

        {/* Right panel — AI Chat */}
        <div style={{ width: 340, flexShrink: 0, height: '100%', overflowY: 'auto', borderLeft: '1px solid #334155' }}>
          <AiChat
            course={currentLesson.course ?? undefined}
            topic={currentLesson.topic ?? undefined}
          />
        </div>
      </div>
    </div>
  );
}
