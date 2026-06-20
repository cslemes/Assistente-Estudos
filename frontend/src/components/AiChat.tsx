import { useRef, useEffect, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { Avatar, Button, Input, Typography } from 'antd';
import { SendOutlined, ClearOutlined, StarOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useAskStream } from '../hooks/useAskStream';
import SourceChip from './SourceChip';

const { Text } = Typography;
const { TextArea } = Input;

interface AiChatProps {
  course?: string;
  topic?: string;
}

function StreamingDots() {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, marginLeft: 4 }}>
      {['-0.3s', '-0.15s', '0s'].map((delay, i) => (
        <span
          key={i}
          style={{
            width: 6, height: 6, borderRadius: '50%', background: '#38bdf8',
            display: 'inline-block', animation: `bounce 1s ${delay} infinite`,
          }}
        />
      ))}
    </span>
  );
}

export default function AiChat({ course, topic }: AiChatProps) {
  const { messages, isStreaming, send, clear } = useAskStream();
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  async function handleSend() {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    setInput('');
    await send(trimmed, course, topic);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#1e293b' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 16px', borderBottom: '1px solid #334155', flexShrink: 0 }}>
        <Avatar
          icon={<StarOutlined />}
          style={{ background: 'linear-gradient(135deg, #38bdf8, #6366f1)', flexShrink: 0 }}
        />
        <div style={{ minWidth: 0, flex: 1 }}>
          <Text strong style={{ color: '#f1f5f9', fontSize: 13, display: 'block', lineHeight: '1.3' }}>
            Assistente
          </Text>
          <Text style={{ color: '#64748b', fontSize: 12 }}>Pergunte sobre esta aula</Text>
        </div>
        {messages.length > 0 && (
          <Button
            type="text"
            size="small"
            icon={<ClearOutlined />}
            onClick={clear}
            disabled={isStreaming}
            style={{ color: '#64748b' }}
            title="Limpar conversa"
          />
        )}
      </div>

      {/* Message thread */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {messages.length === 0 && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            <Text style={{ color: '#475569', fontSize: 13, textAlign: 'center' }}>
              Faça uma pergunta sobre o conteúdo desta aula.
            </Text>
          </div>
        )}

        {messages.map((msg, idx) => {
          const isLast = idx === messages.length - 1;
          return (
            <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {msg.role === 'user' ? (
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <div style={{
                    background: 'rgba(56,189,248,0.08)',
                    border: '1px solid #334155',
                    borderRadius: 8,
                    padding: '8px 12px',
                    maxWidth: '85%',
                  }}>
                    <Text style={{ color: '#7dd3fc', fontSize: 13, fontStyle: 'italic' }}>{msg.content}</Text>
                  </div>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div className="prose prose-sm prose-invert max-w-none
                    prose-p:my-1 prose-headings:text-slate-100 prose-headings:font-semibold
                    prose-h1:text-base prose-h2:text-sm prose-h3:text-sm
                    prose-strong:text-slate-100 prose-em:text-slate-300
                    prose-code:text-sky-300 prose-code:bg-slate-900 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-code:before:content-none prose-code:after:content-none
                    prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-700 prose-pre:rounded-lg prose-pre:text-xs
                    prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5
                    prose-a:text-sky-400 prose-a:no-underline hover:prose-a:underline"
                    style={{ color: '#e2e8f0', fontSize: 13, lineHeight: 1.6 }}
                  >
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                    {isLast && isStreaming && <StreamingDots />}
                  </div>

                  {msg.sources && msg.sources.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {msg.sources
                        .filter((doc, i, arr) => {
                          const key = `${doc.metadata.video_url}|${doc.metadata.start_time}`;
                          return arr.findIndex((d) => `${d.metadata.video_url}|${d.metadata.start_time}` === key) === i;
                        })
                        .map((doc, docIdx) => (
                          <SourceChip key={docIdx} document={doc} />
                        ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div style={{ flexShrink: 0, borderTop: '1px solid #334155', padding: 12 }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8 }}>
          <TextArea
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isStreaming}
            placeholder="Pergunte sobre esta aula…"
            autoSize={{ minRows: 2, maxRows: 4 }}
            style={{ background: '#0f172a', borderColor: '#334155', color: '#f1f5f9', fontSize: 13, resize: 'none' }}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={() => void handleSend()}
            disabled={isStreaming || !input.trim()}
            style={{ flexShrink: 0, height: 36 }}
          />
        </div>
        <Text style={{ color: '#475569', fontSize: 11, marginTop: 6, display: 'block' }}>
          Enter para enviar · Shift+Enter para nova linha
        </Text>
      </div>

      <style>{`
        @keyframes bounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-4px); }
        }
      `}</style>
    </div>
  );
}
