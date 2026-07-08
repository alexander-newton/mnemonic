/**
 * Tests for ChangedCardsPage.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

const { mockUseChangedCards, mockMutate, mockUseApplyCoreChange } = vi.hoisted(() => ({
  mockUseChangedCards: vi.fn(),
  mockMutate: vi.fn(),
  mockUseApplyCoreChange: vi.fn(),
}));

vi.mock('@/hooks/useChangedCards', () => ({
  useChangedCards: mockUseChangedCards,
  useApplyCoreChange: mockUseApplyCoreChange,
}));

import { ChangedCardsPage } from '@/pages/ChangedCardsPage';

const CARD = {
  card_id: 'card-a',
  title: 'Nash equilibrium',
  front: 'What is a [...]?',
  syntax: 'cloze',
  change_kind: 'material',
  core_changed_at: '2026-06-12T09:00:00',
  state: 'review',
  due: '2026-06-20T09:00:00',
  stability: 12.4,
  difficulty: 6.1,
};

beforeEach(() => {
  vi.clearAllMocks();
  mockMutate.mockReset();
  mockUseApplyCoreChange.mockReturnValue({ mutate: mockMutate, isPending: false, error: null });
  mockUseChangedCards.mockReturnValue({
    data: [CARD],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  });
});

describe('ChangedCardsPage', () => {
  it('renders each flagged card with its change kind', () => {
    render(<ChangedCardsPage />);
    expect(screen.getByText('Nash equilibrium')).toBeInTheDocument();
    expect(screen.getByText('material')).toBeInTheDocument();
  });

  it('Keep applies immediately with the keep decision', () => {
    render(<ChangedCardsPage />);
    fireEvent.click(screen.getByRole('button', { name: /keep/i }));
    expect(mockMutate).toHaveBeenCalledWith(
      expect.objectContaining({ cardId: 'card-a', decision: 'keep' }),
      expect.anything(),
    );
  });

  it('Soft reset applies immediately with the soft_reset decision', () => {
    render(<ChangedCardsPage />);
    fireEvent.click(screen.getByRole('button', { name: /soft reset/i }));
    expect(mockMutate).toHaveBeenCalledWith(
      expect.objectContaining({ cardId: 'card-a', decision: 'soft_reset' }),
      expect.anything(),
    );
  });

  it('Full reset asks for confirmation before mutating', async () => {
    render(<ChangedCardsPage />);
    fireEvent.click(screen.getByRole('button', { name: /full reset/i }));
    expect(mockMutate).not.toHaveBeenCalled();
    expect(screen.getByText(/its review history/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /^full reset$/i }));
    await waitFor(() =>
      expect(mockMutate).toHaveBeenCalledWith(
        expect.objectContaining({ cardId: 'card-a', decision: 'full_reset' }),
        expect.anything(),
      ),
    );
  });

  it('shows the empty state when nothing is flagged', () => {
    mockUseChangedCards.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<ChangedCardsPage />);
    expect(screen.getByText(/everything's in sync/i)).toBeInTheDocument();
  });
});
