import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Alert, Card, Progress, Spin, Tabs, Typography } from 'antd';
import { BookOutlined, MessageOutlined, RightOutlined } from '@ant-design/icons';
import { fetchLessons } from '../api';
import type { Lesson } from '../types';
import TopBar from '../components/TopBar';
import AiChat from '../components/AiChat';

const { Title, Text } = Typography;

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

function CourseCard({ name, lessons, onClick }: { name: string; lessons: Lesson[]; onClick: () => void }) {
  const summarized = lessons.filter((l) => l.summary !== null).length;
  const pct = lessons.length > 0 ? Math.round((summarized / lessons.length) * 100) : 0;
  const topics = [...new Set(lessons.map((l) => l.topic ?? 'Sem tópico'))];

  return (
    <Card
      hoverable
      onClick={onClick}
      style={{ background: '#1e293b', borderColor: '#334155', cursor: 'pointer' }}
      styles={{ body: { padding: '20px 24px' } }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
        <Text strong style={{ color: '#f1f5f9', fontSize: 14, lineHeight: 1.4 }}>{name}</Text>
        <RightOutlined style={{ color: '#38bdf8', fontSize: 12, marginTop: 2 }} />
      </div>
      <Text style={{ color: '#64748b', fontSize: 12, display: 'block', marginBottom: 16 }}>
        {topics.slice(0, 3).join(' · ')}{topics.length > 3 ? ` +${topics.length - 3}` : ''}
      </Text>
      <Progress
        percent={pct}
        size={['100%', 6]}
        showInfo={false}
        strokeColor="#38bdf8"
        trailColor="#334155"
        style={{ marginBottom: 8 }}
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text style={{ color: '#64748b', fontSize: 12 }}>{summarized}/{lessons.length} resumidas</Text>
        <Text style={{ color: '#38bdf8', fontSize: 12 }}>{pct}%</Text>
      </div>
    </Card>
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
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Erro ao carregar aulas'))
      .finally(() => setLoading(false));
  }, []);

  const byCourse = groupBy(lessons, (l) => l.course ?? 'Sem curso');
  const summarizedCount = lessons.filter((l) => l.summary !== null).length;

  const tabItems = [
    {
      key: 'courses',
      label: (
        <span>
          <BookOutlined /> Cursos
        </span>
      ),
      children: (
        <div style={{ paddingTop: 24 }}>
          {loading && (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '64px 0' }}>
              <Spin tip="Carregando aulas…" size="large" />
            </div>
          )}

          {error && <Alert type="error" message={error} style={{ marginBottom: 16 }} />}

          {!loading && !error && (
            <>
              <div style={{ marginBottom: 24 }}>
                <Title level={3} style={{ color: '#f1f5f9', margin: 0 }}>Meus Cursos</Title>
                <Text style={{ color: '#64748b', fontSize: 13 }}>
                  {Object.keys(byCourse).length} curso{Object.keys(byCourse).length !== 1 ? 's' : ''} · {summarizedCount} de {lessons.length} aulas resumidas
                </Text>
              </div>

              {lessons.length === 0 && (
                <Text style={{ color: '#64748b' }}>Nenhum curso encontrado.</Text>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
                {Object.entries(byCourse)
                  .sort(([a], [b]) => a.localeCompare(b))
                  .map(([name, cls]) => {
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
        </div>
      ),
    },
    {
      key: 'chat',
      label: (
        <span>
          <MessageOutlined /> Chat
        </span>
      ),
      children: (
        <div style={{ marginTop: 16 }}>
          <AiChat />
        </div>
      ),
    },
  ];

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a' }}>
      <TopBar completedCount={summarizedCount} totalCount={lessons.length} />

      <main style={{ paddingTop: 52, padding: '52px 24px 48px', maxWidth: 1024, margin: '0 auto' }}>
        <Tabs items={tabItems} style={{ marginTop: 8 }} />
      </main>
    </div>
  );
}
