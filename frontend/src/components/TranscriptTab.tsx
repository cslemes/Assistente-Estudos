import { useEffect, useState } from 'react';
import { Alert, Spin, Typography, Empty } from 'antd';
import { fetchSegments } from '../api';
import type { Segment } from '../types';
import { formatTime } from '../utils';

const { Text } = Typography;

interface TranscriptTabProps {
  lessonId: number;
  onSeek: (seconds: number) => void;
}

export default function TranscriptTab({ lessonId, onSeek }: TranscriptTabProps) {
  const [segments, setSegments] = useState<Segment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [empty, setEmpty] = useState(false);

  useEffect(() => {
    setSegments([]);
    setLoading(true);
    setError(null);
    setEmpty(false);

    fetchSegments(lessonId)
      .then((data) => {
        if (data.length === 0) setEmpty(true);
        else setSegments(data);
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : String(err);
        if (msg.includes('404')) setEmpty(true);
        else setError(msg);
      })
      .finally(() => setLoading(false));
  }, [lessonId]);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '48px 0' }}>
        <Spin tip="Carregando transcrição…" />
      </div>
    );
  }

  if (error) return <Alert type="error" message={error} style={{ margin: '16px 0' }} />;

  if (empty) {
    return <Empty description="Transcrição não disponível" style={{ padding: '48px 0' }} />;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {segments.map((seg, idx) => (
        <button
          key={idx}
          onClick={() => onSeek(Math.floor(seg.start))}
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: 12,
            padding: '10px 12px',
            textAlign: 'left',
            background: 'transparent',
            border: 'none',
            borderBottom: '1px solid rgba(51,65,85,0.5)',
            cursor: 'pointer',
            width: '100%',
            transition: 'background 0.15s',
          }}
          onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)')}
          onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = 'transparent')}
        >
          <Text code style={{ color: '#38bdf8', fontSize: 11, minWidth: 40, textAlign: 'right', background: 'transparent', border: 'none', padding: 0 }}>
            {formatTime(seg.start)}
          </Text>
          <Text style={{ color: '#cbd5e1', fontSize: 13, lineHeight: 1.6 }}>{seg.text}</Text>
        </button>
      ))}
    </div>
  );
}
