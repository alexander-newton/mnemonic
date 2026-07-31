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
  variation_id: null,
  variation_front: null,
  variation_answer: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  mockRate.mockResolvedValue({ ok: true });
  mockUseReviewQueue.mockReturnValue({
    data: { cards: [CARD], limits: { minutes_per_session: null } },
    isLoading: false,
    error: null,
  });
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
    mockUseReviewQueue.mockReturnValue({
      data: { cards: [], limits: { minutes_per_session: null } },
      isLoading: false,
      error: null,
    });
    render(<StudyPage />);
    expect(screen.getByText(/nothing due in this deck/i)).toBeInTheDocument();
  });

  it('ends the session when the wall-clock time limit is passed', async () => {
    const nowSpy = vi.spyOn(Date, 'now').mockReturnValue(1_000_000);
    const CARD2 = { ...CARD, card_id: 'c2' };
    mockUseReviewQueue.mockReturnValue({
      data: { cards: [CARD, CARD2], limits: { minutes_per_session: 25 } },
      isLoading: false,
      error: null,
    });
    render(<StudyPage />);
    fireEvent.click(screen.getByRole('button', { name: /show answer/i }));
    // jump the clock 26 minutes past session start before rating
    nowSpy.mockReturnValue(1_000_000 + 26 * 60_000);
    fireEvent.click(screen.getByRole('button', { name: /good/i }));
    await waitFor(() =>
      expect(screen.getByText(/session time limit reached/i)).toBeInTheDocument(),
    );
    nowSpy.mockRestore();
  });

  const VAR_CARD = {
    ...CARD,
    variation_id: 'v1',
    variation_front: 'Rephrased question?',
    variation_answer: 'Rephrased answer.',
  };

  it('renders the variation question and badge when a variation is present', () => {
    mockUseReviewQueue.mockReturnValue({
      data: { cards: [VAR_CARD], limits: { minutes_per_session: null } },
      isLoading: false,
      error: null,
    });
    render(<StudyPage />);
    expect(screen.getByText('Rephrased question?')).toBeInTheDocument();
    expect(screen.queryByText('A [...] equilibrium.')).toBeNull();
    expect(screen.getByText(/variation/i)).toBeInTheDocument();
  });

  it('reveals the variation answer and posts helpfulness with the rating', async () => {
    mockUseReviewQueue.mockReturnValue({
      data: { cards: [VAR_CARD], limits: { minutes_per_session: null } },
      isLoading: false,
      error: null,
    });
    render(<StudyPage />);
    fireEvent.click(screen.getByRole('button', { name: /show answer/i }));
    expect(screen.getByText('Rephrased answer.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /helpful/i }));
    fireEvent.click(screen.getByRole('button', { name: /good/i }));
    expect(mockRate).toHaveBeenCalledWith(
      expect.objectContaining({ card_id: 'c1', rating: 3, variation_id: 'v1', variation_helpful: 1 }),
    );
  });

  it('posts no variation fields for a base card', () => {
    render(<StudyPage />);
    fireEvent.click(screen.getByRole('button', { name: /show answer/i }));
    fireEvent.click(screen.getByRole('button', { name: /good/i }));
    const payload = mockRate.mock.calls[0][0];
    expect(payload.variation_id).toBeUndefined();
    expect(payload.variation_helpful).toBeUndefined();
  });
});
