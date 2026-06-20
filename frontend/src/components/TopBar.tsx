import { Link } from 'react-router-dom';
import { Breadcrumb, Progress, Tooltip, Typography } from 'antd';
import { HomeOutlined, LogoutOutlined } from '@ant-design/icons';
import { signOut } from 'firebase/auth';
import { auth } from '../firebase';

const { Text } = Typography;

interface TopBarProps {
  courseName?: string;
  topicName?: string;
  completedCount: number;
  totalCount: number;
}

export default function TopBar({ courseName, topicName, completedCount, totalCount }: TopBarProps) {
  const pct = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  const breadcrumbItems = [
    {
      title: (
        <Link to="/">
          <HomeOutlined /> Assistente IA
        </Link>
      ),
    },
    ...(courseName ? [{ title: <Text style={{ color: '#94a3b8' }}>{courseName}</Text> }] : []),
    ...(topicName ? [{ title: <Text style={{ color: '#94a3b8' }}>{topicName}</Text> }] : []),
  ];

  return (
    <header
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        height: 52,
        zIndex: 100,
        background: '#1e293b',
        borderBottom: '1px solid #334155',
        display: 'flex',
        alignItems: 'center',
        padding: '0 16px',
        gap: 16,
      }}
    >
      <Breadcrumb items={breadcrumbItems} style={{ flexShrink: 0 }} />

      <div style={{ flex: 1 }} />

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
        <Progress
          percent={pct}
          size={[112, 6]}
          showInfo={false}
          strokeColor="#38bdf8"
          trailColor="#334155"
          style={{ marginBottom: 0 }}
        />
        <Text style={{ color: '#94a3b8', fontSize: 12, whiteSpace: 'nowrap' }}>
          {completedCount}/{totalCount} aulas
        </Text>
      </div>

      <Tooltip title="Sair">
        <LogoutOutlined
          onClick={() => signOut(auth)}
          style={{ color: '#64748b', fontSize: 16, cursor: 'pointer' }}
          onMouseEnter={e => (e.currentTarget.style.color = '#f87171')}
          onMouseLeave={e => (e.currentTarget.style.color = '#64748b')}
        />
      </Tooltip>
    </header>
  );
}
