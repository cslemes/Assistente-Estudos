import { useState } from 'react';
import { signInWithRedirect } from 'firebase/auth';
import { Alert, Button, Typography } from 'antd';
import { auth, googleProvider } from '../firebase';

const { Title, Text } = Typography;

export default function Login() {
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  async function handleSignIn() {
    setLoading(true);
    setError(null);
    try {
      await signInWithRedirect(auth, googleProvider);
    } catch (e: unknown) {
      console.error('Auth error:', e);
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0f172a',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      <div style={{
        background: '#1e293b',
        border: '1px solid #334155',
        borderRadius: 16,
        padding: '48px 40px',
        width: 360,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 24,
      }}>
        <div style={{ textAlign: 'center' }}>
          <Title level={3} style={{ color: '#f1f5f9', margin: 0 }}>
            Assistente de Estudos
          </Title>
          <Text style={{ color: '#64748b', fontSize: 13 }}>
            PUC-Rio · Pós-Graduação em IA
          </Text>
        </div>

        {error && <Alert type="error" message={error} style={{ width: '100%' }} />}

        <Button
          size="large"
          loading={loading}
          onClick={() => void handleSignIn()}
          style={{
            width: '100%',
            height: 44,
            background: '#fff',
            color: '#1e293b',
            border: 'none',
            borderRadius: 8,
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 10,
          }}
          icon={
            <svg width="18" height="18" viewBox="0 0 48 48" style={{ flexShrink: 0 }}>
              <path fill="#FFC107" d="M43.6 20.1H42V20H24v8h11.3C33.6 32.9 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.1 7.9 3l5.7-5.7C34.5 6.5 29.6 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.6-.4-3.9z"/>
              <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.5 16 19 13 24 13c3.1 0 5.8 1.1 7.9 3l5.7-5.7C34.5 6.5 29.6 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/>
              <path fill="#4CAF50" d="M24 44c5.4 0 10.3-2.1 14-5.4l-6.5-5.5C29.5 34.9 26.9 36 24 36c-5.2 0-9.6-3.5-11.2-8.3l-6.5 5C9.5 39.4 16.3 44 24 44z"/>
              <path fill="#1976D2" d="M43.6 20.1H42V20H24v8h11.3c-.8 2.3-2.3 4.2-4.2 5.5l6.5 5.5C37.3 37 44 32 44 24c0-1.3-.1-2.6-.4-3.9z"/>
            </svg>
          }
        >
          {loading ? 'Entrando…' : 'Entrar com Google'}
        </Button>

        <Text style={{ color: '#475569', fontSize: 11, textAlign: 'center' }}>
          Acesso restrito a membros do programa
        </Text>
      </div>
    </div>
  );
}
