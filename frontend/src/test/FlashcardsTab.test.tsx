import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import FlashcardsTab from '../components/FlashcardsTab';
import * as api from '../api';
import type { Lesson } from '../types';

const lesson: Lesson = {
  id: 7,
  course: 'DL Python',
  topic: 'Autoencoder',
  aula_number: 3,
  video_url: null,
  summary: null,
  summarized: false,
  status: 'sent',
  file_path: '',
  created_at: '',
};

beforeEach(() => {
  vi.restoreAllMocks();
});

describe('FlashcardsTab', () => {
  it('renders the slider defaulting to 20 cards', () => {
    render(<FlashcardsTab lesson={lesson} />);
    expect(screen.getByRole('slider')).toHaveValue('20');
  });

  it('updates card count label when slider moves', () => {
    render(<FlashcardsTab lesson={lesson} />);
    const slider = screen.getByRole('slider');

    fireEvent.change(slider, { target: { value: '30' } });

    expect(screen.getByText(/30/)).toBeInTheDocument();
  });

  it('renders deck name input as empty by default', () => {
    render(<FlashcardsTab lesson={lesson} />);
    expect(screen.getByPlaceholderText(/Nome do deck/)).toHaveValue('');
  });

  it('calls downloadFlashcards with lesson data when button clicked', async () => {
    const fakeBlob = new Blob(['x']);
    const spy = vi.spyOn(api, 'downloadFlashcards').mockResolvedValue(fakeBlob);

    // Stub URL APIs used for download
    vi.stubGlobal('URL', { createObjectURL: vi.fn(() => 'blob:fake'), revokeObjectURL: vi.fn() });

    render(<FlashcardsTab lesson={lesson} />);
    await userEvent.click(screen.getByRole('button', { name: /Baixar/i }));

    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith(expect.objectContaining({
        course: 'DL Python',
        topic: 'Autoencoder',
        aula_number: 3,
        num_cards: 20,
      }));
    });
  });

  it('shows error message when download fails', async () => {
    vi.spyOn(api, 'downloadFlashcards').mockRejectedValue(new Error('Network error'));

    render(<FlashcardsTab lesson={lesson} />);
    await userEvent.click(screen.getByRole('button', { name: /Baixar/i }));

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });

  it('disables download button while generating', async () => {
    let resolve!: (b: Blob) => void;
    vi.spyOn(api, 'downloadFlashcards').mockReturnValue(new Promise((r) => { resolve = r; }));
    vi.stubGlobal('URL', { createObjectURL: vi.fn(() => 'blob:fake'), revokeObjectURL: vi.fn() });

    render(<FlashcardsTab lesson={lesson} />);
    await userEvent.click(screen.getByRole('button', { name: /Baixar/i }));

    expect(screen.getByRole('button')).toBeDisabled();
    resolve(new Blob(['x']));
  });
});
