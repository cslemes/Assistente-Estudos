import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CourseSidebar from '../components/CourseSidebar';
import type { Lesson } from '../types';

const lessons: Lesson[] = [
  { id: 1, course: 'DL', topic: 'Autoencoder', aula_number: 1, video_url: null, summary: null, summarized: false, status: 'pending', file_path: '', created_at: '' },
  { id: 2, course: 'DL', topic: 'Autoencoder', aula_number: 2, video_url: null, summary: 'ok', summarized: true, status: 'sent', file_path: '', created_at: '' },
  { id: 3, course: 'DL', topic: 'GAN', aula_number: 1, video_url: null, summary: null, summarized: false, status: 'pending', file_path: '', created_at: '' },
];

describe('CourseSidebar', () => {
  it('renders a section header for each topic', () => {
    render(<CourseSidebar lessons={lessons} currentId={1} onSelect={vi.fn()} />);

    expect(screen.getByText('Autoencoder')).toBeInTheDocument();
    expect(screen.getByText('GAN')).toBeInTheDocument();
  });

  it('renders a button for each lesson with its aula number', () => {
    render(<CourseSidebar lessons={lessons} currentId={1} onSelect={vi.fn()} />);

    // lessons 1 and 3 both have aula_number 1 (different topics) → 2 matches
    expect(screen.getAllByText('Aula 1', { selector: 'p' })).toHaveLength(2);
    expect(screen.getAllByText('Aula 2', { selector: 'p' })).toHaveLength(1);
  });

  it('highlights the current lesson with sky-400 text', () => {
    render(<CourseSidebar lessons={lessons} currentId={1} onSelect={vi.fn()} />);

    const currentLabel = screen.getAllByText('Aula 1', { selector: 'p' })[0];
    expect(currentLabel).toHaveClass('text-sky-400');
  });

  it('shows done icon for summarized lessons', () => {
    render(<CourseSidebar lessons={lessons} currentId={1} onSelect={vi.fn()} />);

    const doneIcons = screen.getAllByText('✓');
    expect(doneIcons).toHaveLength(1);
  });

  it('calls onSelect with lesson id when a lesson button is clicked', async () => {
    const onSelect = vi.fn();
    render(<CourseSidebar lessons={lessons} currentId={1} onSelect={onSelect} />);

    const buttons = screen.getAllByRole('button');
    await userEvent.click(buttons[1]); // second lesson in Autoencoder topic

    expect(onSelect).toHaveBeenCalledWith(2);
  });

  it('sorts lessons within a topic by aula_number', () => {
    const reversed: Lesson[] = [
      { ...lessons[1], id: 2, aula_number: 2 },
      { ...lessons[0], id: 1, aula_number: 1 },
    ];
    render(<CourseSidebar lessons={reversed} currentId={99} onSelect={vi.fn()} />);

    const aulaLabels = screen.getAllByText(/Aula \d/, { selector: 'p' });
    expect(aulaLabels[0]).toHaveTextContent('Aula 1');
    expect(aulaLabels[1]).toHaveTextContent('Aula 2');
  });
});
