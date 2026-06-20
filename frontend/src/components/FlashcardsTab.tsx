import { useState } from 'react';
import { Alert, Button, Card, Form, Input, Slider, Typography } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import { downloadFlashcards } from '../api';
import type { Lesson } from '../types';

const { Text, Paragraph } = Typography;

interface FlashcardsTabProps {
  lesson: Lesson;
}

export default function FlashcardsTab({ lesson }: FlashcardsTabProps) {
  const [numCards, setNumCards] = useState(20);
  const [deckName, setDeckName] = useState('');
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDownload() {
    setDownloading(true);
    setError(null);
    try {
      const blob = await downloadFlashcards({
        course: lesson.course ?? undefined,
        topic: lesson.topic ?? undefined,
        aula_number: lesson.aula_number ?? undefined,
        num_cards: numCards,
        deck_name: deckName || undefined,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${deckName || 'flashcards'}.apkg`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao gerar flashcards');
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div style={{ paddingTop: 16, maxWidth: 480 }}>
      <Paragraph style={{ color: '#94a3b8', fontSize: 13 }}>
        Gera um deck Anki (.apkg) com flashcards extraídos do conteúdo desta aula.
      </Paragraph>

      <Card style={{ background: '#1e293b', borderColor: '#334155' }}>
        <Form layout="vertical" style={{ gap: 0 }}>
          <Form.Item
            label={
              <span>
                <Text style={{ color: '#cbd5e1' }}>Número de cartões: </Text>
                <Text strong style={{ color: '#38bdf8' }}>{numCards}</Text>
              </span>
            }
          >
            <Slider
              min={5}
              max={50}
              value={numCards}
              onChange={setNumCards}
              tooltip={{ formatter: (v) => `${v} cartões` }}
              marks={{ 5: '5', 50: '50' }}
            />
          </Form.Item>

          <Form.Item label={<Text style={{ color: '#cbd5e1' }}>Nome do deck</Text>}>
            <Input
              placeholder="Nome do deck (opcional)"
              value={deckName}
              onChange={(e) => setDeckName(e.target.value)}
              style={{ background: '#0f172a', borderColor: '#334155' }}
            />
          </Form.Item>

          {error && <Alert type="error" message={error} style={{ marginBottom: 16 }} />}

          <Button
            type="primary"
            icon={<DownloadOutlined />}
            loading={downloading}
            onClick={() => void handleDownload()}
            block
          >
            {downloading ? 'Gerando deck…' : 'Baixar .apkg'}
          </Button>
        </Form>
      </Card>
    </div>
  );
}
