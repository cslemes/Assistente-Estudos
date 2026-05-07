import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchLessons, downloadFlashcards } from '../api';

const mockLesson = {
  id: 1,
  course: 'DL Python',
  topic: 'Autoencoder',
  aula_number: 3,
  video_url: 'https://youtu.be/abc',
  summary: null,
  summarized: false,
  status: 'pending',
  file_path: 'D:\\Downloads\\DL Python\\Autoencoder\\video\\Aula_03.mp4',
  created_at: '2024-01-01',
};

beforeEach(() => {
  vi.resetAllMocks();
});

describe('fetchLessons', () => {
  it('returns parsed lesson array on success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([mockLesson]),
    }));

    const lessons = await fetchLessons();

    expect(lessons).toHaveLength(1);
    expect(lessons[0].course).toBe('DL Python');
    expect(lessons[0].aula_number).toBe(3);
  });

  it('throws when response is not ok', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
    }));

    await expect(fetchLessons()).rejects.toThrow('fetchLessons failed: 500');
  });

  it('calls the correct endpoint', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    });
    vi.stubGlobal('fetch', mockFetch);

    await fetchLessons();

    expect(mockFetch).toHaveBeenCalledWith('/api/summarize');
  });
});

describe('downloadFlashcards', () => {
  it('posts request body and returns blob on success', async () => {
    const fakeBlob = new Blob(['data'], { type: 'application/octet-stream' });
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      blob: () => Promise.resolve(fakeBlob),
    });
    vi.stubGlobal('fetch', mockFetch);

    const result = await downloadFlashcards({ num_cards: 10, course: 'DL Python' });

    expect(result).toBe(fakeBlob);
    expect(mockFetch).toHaveBeenCalledWith('/api/flashcards', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ num_cards: 10, course: 'DL Python' }),
    }));
  });

  it('throws when response is not ok', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
    }));

    await expect(downloadFlashcards({ num_cards: 5 })).rejects.toThrow('downloadFlashcards failed: 404');
  });
});
