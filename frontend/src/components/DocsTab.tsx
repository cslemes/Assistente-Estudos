import { useEffect, useState } from 'react';
import { Alert, Button, Empty, Spin, Tag, Tooltip, Typography } from 'antd';
import {
  CloudOutlined,
  CodeOutlined,
  DownloadOutlined,
  FileExcelOutlined,
  FileImageOutlined,
  FileOutlined,
  FilePdfOutlined,
  FilePptOutlined,
  FileTextOutlined,
  FileWordOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

interface DocFile {
  name: string;
  path: string;
  category: string;
  size: number;
  mime_type: string;
  extension: string;
  url: string | null;       // public storage URL when uploaded, else null
  in_storage: boolean;
}

function fileIcon(ext: string) {
  const e = ext.toLowerCase();
  if (e === 'pdf')                              return <FilePdfOutlined   style={{ color: '#f87171' }} />;
  if (e === 'docx' || e === 'doc')              return <FileWordOutlined  style={{ color: '#60a5fa' }} />;
  if (e === 'pptx' || e === 'ppt')              return <FilePptOutlined  style={{ color: '#fb923c' }} />;
  if (e === 'xlsx' || e === 'xls' || e === 'csv') return <FileExcelOutlined style={{ color: '#4ade80' }} />;
  if (e === 'ipynb' || e === 'py')              return <CodeOutlined      style={{ color: '#a78bfa' }} />;
  if (e === 'md'  || e === 'txt')               return <FileTextOutlined  style={{ color: '#94a3b8' }} />;
  if (['jpg','jpeg','png','gif'].includes(e))   return <FileImageOutlined style={{ color: '#f472b6' }} />;
  return <FileOutlined style={{ color: '#94a3b8' }} />;
}

function formatSize(bytes: number): string {
  if (bytes < 1024)      return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}

const API_BASE = import.meta.env.VITE_API_URL ?? '/api';
const API_KEY  = import.meta.env.VITE_BACKEND_API_KEY as string | undefined;

function apiHeaders(): Record<string, string> {
  return API_KEY ? { 'X-Api-Key': API_KEY } : {};
}

function downloadHref(lessonId: number, doc: DocFile): string {
  // If the file is in object storage, use the direct public URL.
  // Otherwise fall back to the API download endpoint which serves it locally.
  return doc.url ?? `${API_BASE}/lessons/${lessonId}/documents/download?file=${encodeURIComponent(doc.path)}`;
}

export default function DocsTab({ lessonId }: { lessonId: number }) {
  const [docs, setDocs]       = useState<DocFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(`${API_BASE}/lessons/${lessonId}/documents`, { headers: apiHeaders() })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<DocFile[]>;
      })
      .then(setDocs)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [lessonId]);

  if (loading) return <div style={{ padding: 24, textAlign: 'center' }}><Spin /></div>;
  if (error)   return <Alert type="error" message={`Erro ao carregar documentos: ${error}`} style={{ margin: 16 }} />;
  if (!docs.length) return <Empty description="Nenhum documento disponível para esta aula." style={{ marginTop: 32 }} />;

  const documents = docs.filter((d) => d.category === 'document');
  const notebooks  = docs.filter((d) => d.category === 'notebook');

  const renderGroup = (title: string, items: DocFile[]) => {
    if (!items.length) return null;
    return (
      <div style={{ marginBottom: 24 }}>
        <Text style={{ color: '#64748b', fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1 }}>
          {title}
        </Text>
        <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
          {items.map((doc) => (
            <div
              key={doc.path}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '8px 12px',
                background: '#1e293b',
                borderRadius: 8,
                border: '1px solid #334155',
              }}
            >
              <span style={{ fontSize: 18, flexShrink: 0 }}>{fileIcon(doc.extension)}</span>

              <div style={{ flex: 1, minWidth: 0 }}>
                <Tooltip title={doc.name}>
                  <Text style={{ color: '#e2e8f0', fontSize: 13, display: 'block' }} ellipsis>
                    {doc.name}
                  </Text>
                </Tooltip>
                <Text style={{ color: '#475569', fontSize: 11 }}>{formatSize(doc.size)}</Text>
              </div>

              <Tag color="default" style={{ fontSize: 10, margin: 0, flexShrink: 0 }}>
                {doc.extension.toUpperCase()}
              </Tag>

              {doc.in_storage && (
                <Tooltip title="Disponível no object storage">
                  <CloudOutlined style={{ color: '#38bdf8', fontSize: 13, flexShrink: 0 }} />
                </Tooltip>
              )}

              <Button
                type="text"
                size="small"
                icon={<DownloadOutlined />}
                href={downloadHref(lessonId, doc)}
                target={doc.in_storage ? '_blank' : undefined}
                download={doc.in_storage ? undefined : doc.name}
                style={{ color: '#38bdf8', flexShrink: 0 }}
              />
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div style={{ paddingTop: 16 }}>
      {renderGroup('Documentos', documents)}
      {renderGroup('Scripts & Notebooks', notebooks)}
    </div>
  );
}
