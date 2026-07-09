/** Tests for the StudyPage review flow. */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

const { mockUseReviewQueue, mockRate } = vi.hoisted(() => ({
  mockUseReviewQueue: vi.fn(),
  mockRate: vi.fn(),
}));

vi.mock('@/hooks/useReviewQueue', () => ({ useReviewQueue: mockUseReviewQueue }));
vi.mock('@/services/api', () => ({ api: { rate: mockRate } }));
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useParams: () => ({ deckId: 'gt' }), useNavigate: () => vi.fn() };
});
vi.mock('@/components/review/CardContent', () => ({
  CardContent: ({ markdown }: { markdown: string }) => <div>{markdown}</div>,
}));

import { StudyPage } from '@/pages/StudyPage';

const CARD = {
  card_id: 'c1',
  syntax: 'cloze',
  front: 'A [...] equilibrium.',
  answer: 'A **Nash** equilibrium.',
  previews: { '1': 0, '2': 1, '3': 4, '4': 9 },
};

beforeEach(() => {
  vi.clearAllMocks();
  mockRate.mockResolvedValue({ ok: true });
  mockUseReviewQueue.mockReturnValue({ data: [CARD], isLoading: false, error: null });
});

describe('StudyPage', () => {
  it('shows the front and hides rating buttons until revealed', () => {
    render(<StudyPage />);
    expect(screen.getByText('A [...] equilibrium.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /good/i })).toBeNull();
    expect(screen.getByRole('button', { name: /show answer/i })).toBeInTheDocument();
  });

  it('reveals the answer and rates, advancing to the summary', async () => {
    render(<StudyPage />);
    fireEvent.click(screen.getByRole('button', { name: /show answer/i }));
    expect(screen.getByText('A **Nash** equilibrium.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /good/i }));
    expect(mockRate).toHaveBeenCalledWith(expect.objectContaining({ card_id: 'c1', rating: 3 }));
    await waitFor(() => expect(screen.getByText(/reviewed 1 card/i)).toBeInTheDocument());
  });

  it('shows an empty state when nothing is due', () => {
    mockUseReviewQueue.mockReturnValue({ data: [], isLoading: false, error: null });
    render(<StudyPage />);
    expect(screen.getByText(/nothing due in this deck/i)).toBeInTheDocument();
  });
});
