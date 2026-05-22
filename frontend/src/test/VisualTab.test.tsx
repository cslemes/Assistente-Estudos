import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import VisualTab from '../components/VisualTab';
import * as api from '../api';
import type { VisualChunk } from '../types';

const chunks: VisualChunk[] = [
  { source_type: 'slide',      text: 'Intro to CNN',     start_time: 60,  video_url: 'https://youtu.be/abc?t=60',  slide_thumb: null },
  { source_type: 'notebook',   text: 'model.fit(X, y)',  start_time: 120, video_url: 'https://youtu.be/abc?t=120', slide_thumb: null },
  { source_type: 'whiteboard', text: 'Loss = CE + L2',   start_time: 180, video_url: 'https://youtu.be/abc?t=180', slide_thumb: null },
];

beforeEach(() => {
  vi.restoreAllMocks();
});

describe('VisualTab', () => {
  it('shows loading state before data arrives', () => {
    vi.spyOn(api, 'fetchVisualChunks').mockReturnValue(new Promise(() => {}));
    render(<VisualTab lessonId={1} onSeek={vi.fn()} />);

    expect(screen.getByText(/Carregando/i)).toBeInTheDocument();
  });

  it('renders one item per chunk after loading', async () => {
    vi.spyOn(api, 'fetchVisualChunks').mockResolvedValue(chunks);
    render(<VisualTab lessonId={1} onSeek={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Intro to CNN')).toBeInTheDocument();
      expect(screen.getByText('model.fit(X, y)')).toBeInTheDocument();
      expect(screen.getByText('Loss = CE + L2')).toBeInTheDocument();
    });
  });

  it('shows empty state when no visual chunks exist', async () => {
    vi.spyOn(api, 'fetchVisualChunks').mockResolvedValue([]);
    render(<VisualTab lessonId={1} onSeek={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText(/Nenhum conteúdo visual/i)).toBeInTheDocument();
    });
  });

  it('displays source_type badge for each item', async () => {
    vi.spyOn(api, 'fetchVisualChunks').mockResolvedValue(chunks);
    render(<VisualTab lessonId={1} onSeek={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('slide')).toBeInTheDocument();
      expect(screen.getByText('notebook')).toBeInTheDocument();
      expect(screen.getByText('whiteboard')).toBeInTheDocument();
    });
  });

  it('calls onSeek with start_time when item is clicked', async () => {
    vi.spyOn(api, 'fetchVisualChunks').mockResolvedValue(chunks);
    const onSeek = vi.fn();
    render(<VisualTab lessonId={1} onSeek={onSeek} />);

    await waitFor(() => screen.getByText('Intro to CNN'));
    await userEvent.click(screen.getByText('Intro to CNN').closest('button')!);

    expect(onSeek).toHaveBeenCalledWith(60);
  });

  it('shows formatted timestamp for each item', async () => {
    vi.spyOn(api, 'fetchVisualChunks').mockResolvedValue(chunks);
    render(<VisualTab lessonId={1} onSeek={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('1:00')).toBeInTheDocument();
      expect(screen.getByText('2:00')).toBeInTheDocument();
      expect(screen.getByText('3:00')).toBeInTheDocument();
    });
  });
});
