import { useEffect, useState } from 'react';
import { Alert, Button, Card, Empty, Spin, Tag, Typography } from 'antd';
import { ClockCircleOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { fetchHighlights, generateHighlights } from '../api';
import type { Highlight } from '../types';
import { formatTime } from '../utils';

const { Text, Paragraph } = Typography;

interface HighlightsTabProps {
  lessonId: number;
  onSeek: (seconds: number) => void;
}

export default function HighlightsTab({ lessonId, onSeek }: HighlightsTabProps) {
  const [highlights, setHighlights] = useState<Highlight[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setNotFound(false);

    fetchHighlights(lessonId)
      .then((data) => setHighlights(data.highlights))
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : String(err);
        if (msg.includes('404')) setNotFound(true);
        else setError(msg);
      })
      .finally(() => setLoading(false));
  }, [lessonId]);

  function handleGenerate() {
    setGenerating(true);
    setError(null);
    generateHighlights(lessonId, 5)
      .then((data) => {
        setHighlights(data.highlights);
        setNotFound(false);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setGenerating(false));
  }

  if (loading || generating) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '48px 0' }}>
        <Spin tip={generating ? 'Gerando highlights…' : 'Carregando highlights…'} />
      </div>
    );
  }

  if (error) return <Alert type="error" message={error} style={{ margin: '16px 0' }} />;

  if (notFound) {
    return (
      <Empty description="Nenhum highlight disponível para esta aula." style={{ padding: '48px 0' }}>
        <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleGenerate}>
          Gerar Highlights
        </Button>
      </Empty>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '12px 0' }}>
      {highlights.map((hl, idx) => (
        <Card
          key={idx}
          size="small"
          style={{ background: '#1e293b', borderColor: '#334155' }}
          styles={{ body: { padding: '12px 16px' } }}
        >
          <Text strong style={{ color: '#38bdf8', fontSize: 13, display: 'block', marginBottom: 6 }}>
            {hl.title}
          </Text>
          <Paragraph style={{ color: '#cbd5e1', fontSize: 13, margin: '0 0 10px' }}>
            {hl.description}
          </Paragraph>
          <Tag
            icon={<ClockCircleOutlined />}
            style={{ cursor: 'pointer', fontFamily: 'monospace', background: 'transparent', borderColor: '#38bdf8', color: '#38bdf8' }}
            onClick={() => onSeek(hl.start_time)}
          >
            {formatTime(hl.start_time)}
          </Tag>
        </Card>
      ))}
    </div>
  );
}
