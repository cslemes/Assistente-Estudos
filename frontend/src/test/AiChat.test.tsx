import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AiChat from '../components/AiChat';
import * as useAskStreamModule from '../hooks/useAskStream';

const mockSend = vi.fn();
const mockClear = vi.fn();

function stubStream(overrides: Partial<ReturnType<typeof useAskStreamModule.useAskStream>> = {}) {
  vi.spyOn(useAskStreamModule, 'useAskStream').mockReturnValue({
    messages: [],
    isStreaming: false,
    send: mockSend,
    clear: mockClear,
    ...overrides,
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
  mockSend.mockClear().mockResolvedValue(undefined);
  mockClear.mockClear();
});

describe('AiChat', () => {
  it('renders the textarea and send button', () => {
    stubStream();
    render(<AiChat />);

    expect(screen.getByRole('textbox')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /enviar/i })).toBeInTheDocument();
  });

  it('send button is disabled when input is empty', () => {
    stubStream();
    render(<AiChat />);

    expect(screen.getByRole('button', { name: /enviar/i })).toBeDisabled();
  });

  it('send button enables when user types', async () => {
    stubStream();
    render(<AiChat />);

    await userEvent.type(screen.getByRole('textbox'), 'hello');

    expect(screen.getByRole('button', { name: /enviar/i })).not.toBeDisabled();
  });

  it('calls send with trimmed input on button click', async () => {
    stubStream();
    render(<AiChat course="DL" topic="CNN" />);

    await userEvent.type(screen.getByRole('textbox'), '  what is backprop?  ');
    await userEvent.click(screen.getByRole('button', { name: /enviar/i }));

    await waitFor(() => {
      expect(mockSend).toHaveBeenCalledWith('what is backprop?', 'DL', 'CNN');
    });
  });

  it('clears input after sending', async () => {
    stubStream();
    render(<AiChat />);
    const textarea = screen.getByRole('textbox');

    await userEvent.type(textarea, 'a question');
    await userEvent.click(screen.getByRole('button', { name: /enviar/i }));

    await waitFor(() => {
      expect(textarea).toHaveValue('');
    });
  });

  it('sends on Enter but not on Shift+Enter', async () => {
    stubStream();
    render(<AiChat />);
    const textarea = screen.getByRole('textbox');

    await userEvent.type(textarea, 'hello{shift>}{enter}{/shift}');
    expect(mockSend).not.toHaveBeenCalled();

    await userEvent.type(textarea, '{enter}');
    await waitFor(() => expect(mockSend).toHaveBeenCalledTimes(1));
  });

  it('disables textarea and button while streaming', () => {
    stubStream({ isStreaming: true });
    render(<AiChat />);

    expect(screen.getByRole('textbox')).toBeDisabled();
    expect(screen.getByRole('button', { name: /enviar/i })).toBeDisabled();
  });

  it('shows Limpar button when there are messages', () => {
    stubStream({
      messages: [{ role: 'user', content: 'hello' }],
    });
    render(<AiChat />);

    expect(screen.getByRole('button', { name: /limpar/i })).toBeInTheDocument();
  });

  it('does not show Limpar button with no messages', () => {
    stubStream();
    render(<AiChat />);

    expect(screen.queryByRole('button', { name: /limpar/i })).not.toBeInTheDocument();
  });

  it('calls clear when Limpar is clicked', async () => {
    stubStream({ messages: [{ role: 'user', content: 'hi' }] });
    render(<AiChat />);

    await userEvent.click(screen.getByRole('button', { name: /limpar/i }));

    expect(mockClear).toHaveBeenCalledOnce();
  });
});
