import { Badge, Typography } from 'antd';
import type { Lesson } from '../types';

const { Text } = Typography;

interface CourseSidebarProps {
  lessons: Lesson[];
  currentId: number;
  watched: Set<number>;
  onSelect: (id: number) => void;
}

function StatusDot({ done, current }: { done: boolean; current: boolean }) {
  if (current) return <Badge color="#38bdf8" />;
  if (done) return <Badge color="#34d399" />;
  return <Badge color="#475569" />;
}

export default function CourseSidebar({ lessons, currentId, watched, onSelect }: CourseSidebarProps) {
  const byTopic = lessons.reduce<Record<string, Lesson[]>>((acc, l) => {
    const key = l.topic ?? 'Sem tópico';
    (acc[key] ??= []).push(l);
    return acc;
  }, {});

  Object.values(byTopic).forEach((group) =>
    group.sort((a, b) => (a.aula_number ?? 0) - (b.aula_number ?? 0)),
  );

  const sortedTopics = Object.entries(byTopic).sort(([, a], [, b]) => {
    const minA = Math.min(...a.map((l) => l.aula_number ?? 0));
    const minB = Math.min(...b.map((l) => l.aula_number ?? 0));
    return minA - minB;
  });

  return (
    <aside style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', background: '#1e293b', overflowY: 'auto' }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #334155', flexShrink: 0 }}>
        <Text strong style={{ color: '#f1f5f9', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Conteúdo do Curso
        </Text>
      </div>

      <nav style={{ flex: 1, paddingBlock: 8 }}>
        {sortedTopics.map(([topicName, topicLessons]) => (
          <div key={topicName}>
            <div style={{ padding: '16px 16px 4px' }}>
              <Text style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#38bdf8' }}>
                {topicName}
              </Text>
            </div>

            {topicLessons.map((lesson) => {
              const isCurrent = lesson.id === currentId;
              const isDone = watched.has(lesson.id);

              return (
                <button
                  key={lesson.id}
                  onClick={() => onSelect(lesson.id)}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '10px 16px',
                    paddingLeft: isCurrent ? 14 : 16,
                    textAlign: 'left',
                    background: isCurrent ? 'rgba(56,189,248,0.08)' : 'transparent',
                    border: 'none',
                    borderLeft: isCurrent ? '2px solid #38bdf8' : '2px solid transparent',
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                  onMouseEnter={(e) => {
                    if (!isCurrent) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)';
                  }}
                  onMouseLeave={(e) => {
                    if (!isCurrent) (e.currentTarget as HTMLElement).style.background = 'transparent';
                  }}
                >
                  <StatusDot done={isDone} current={isCurrent} />
                  <Text
                    style={{
                      fontSize: 13,
                      fontWeight: 500,
                      color: isCurrent ? '#38bdf8' : isDone ? '#cbd5e1' : '#94a3b8',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {lesson.aula_number != null ? `Aula ${lesson.aula_number}` : 'Aula —'}
                  </Text>
                </button>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}
