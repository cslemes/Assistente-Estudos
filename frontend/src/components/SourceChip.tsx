import { Tag, Tooltip } from 'antd';
import { ClockCircleOutlined } from '@ant-design/icons';
import type { Document } from '../types';
import { formatTime } from '../utils';

interface SourceChipProps {
  document: Document;
}

export default function SourceChip({ document }: SourceChipProps) {
  const { metadata } = document;
  const hasLink = Boolean(metadata.video_url);

  const label = [
    metadata.start_time != null ? formatTime(metadata.start_time) : null,
    metadata.course,
    metadata.aula_number != null ? `Aula ${metadata.aula_number}` : null,
  ]
    .filter(Boolean)
    .join(' · ');

  const tag = (
    <Tag
      icon={<ClockCircleOutlined />}
      color="default"
      style={{
        cursor: hasLink ? 'pointer' : 'default',
        background: '#0f172a',
        borderColor: '#334155',
        color: '#94a3b8',
        fontSize: 11,
        marginBottom: 0,
      }}
      onClick={() => {
        if (hasLink) window.open(metadata.video_url!, '_blank', 'noopener,noreferrer');
      }}
    >
      {label || '—'}
    </Tag>
  );

  return hasLink ? <Tooltip title="Abrir no YouTube">{tag}</Tooltip> : tag;
}
