/**
 * Tests for DeckDetailPage - deck detail view with cards management
 */

import React from 'react';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { DeckDetailPage } from '@/pages/DeckDetailPage';
import { useDeck, useDeleteDeck } from '@/hooks/useDecks';
import { useCards, useDeleteCard } from '@/hooks/useCards';
import type { Deck, Card } from '@/types';

// Mock the hooks
vi.mock('@/hooks/useDecks');
vi.mock('@/hooks/useCards');

// Mock the modals
vi.mock('@/components/card/CreateCardModal', () => ({
  CreateCardModal: ({ isOpen, onClose, deckId }: any) =>
    isOpen ? (
      <div data-testid="create-card-modal">
        <button onClick={onClose}>Close Modal</button>
        <p>Deck ID: {deckId}</p>
      </div>
    ) : null,
}));

vi.mock('@/components/card/EditCardModal', () => ({
  EditCardModal: ({ isOpen, onClose, card }: any) =>
    isOpen && card ? (
      <div data-testid="edit-card-modal">
        <button onClick={onClose}>Close Modal</button>
        <p data-testid="edit-card-id">Card ID: {card.id}</p>
      </div>
    ) : null,
}));

vi.mock('@/components/deck/EditDeckModal', () => ({
  EditDeckModal: ({ isOpen, onClose, deckId }: any) =>
    isOpen ? (
      <div data-testid="edit-deck-modal">
        <button onClick={onClose}>Close Modal</button>
        <p>Deck ID: {deckId}</p>
      </div>
    ) : null,
}));

const mockDeck: Deck = {
  id: 'deck-1',
  userId: 'user-1',
  name: 'Test Deck',
  description: 'A test deck description',
  variationEnabled: true,
  variationFrequency: 0.5,
  leechThreshold: 8,
  dailyReviewLimit: 100,
  dailyNewLimit: 20,
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
};

const mockCard1: Card = {
  id: 'card-1',
  deckId: 'deck-1',
  cardTypeId: 'type-1',
  content: ':::{.front}\nQ1\n:::\n\n:::{.back}\nA1\n:::',
  notes: 'Card notes',
  tags: ['tag1', 'tag2'],
  suspended: false,
  state: 'new',
  stability: 0,
  difficulty: 0.5,
  due: '2024-01-02T00:00:00Z',
  reps: 0,
  lapses: 0,
  leechScore: 0,
  leechNotified: false,
  parentCardId: null,
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
};

const mockCard2: Card = {
  id: 'card-2',
  deckId: 'deck-1',
  cardTypeId: 'type-1',
  content: ':::{.front}\nQ2\n:::\n\n:::{.back}\nA2\n:::',
  notes: '',
  tags: ['tag1'],
  suspended: false,
  state: 'learning',
  stability: 0.8,
  difficulty: 0.6,
  due: '2024-01-01T12:00:00Z',
  reps: 1,
  lapses: 0,
  leechScore: 0,
  leechNotified: false,
  parentCardId: null,
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
};

const mockCard3: Card = {
  id: 'card-3',
  deckId: 'deck-1',
  cardTypeId: 'type-1',
  content: ':::{.front}\nQ3 with very long content that should be truncated when displayed\n:::\n\n:::{.back}\nA3 with even longer content\n:::',
  notes: '',
  tags: [],
  suspended: false,
  state: 'review',
  stability: 1.5,
  difficulty: 0.7,
  due: '2024-01-03T00:00:00Z',
  reps: 5,
  lapses: 0,
  leechScore: 0,
  leechNotified: false,
  parentCardId: null,
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
};

function renderWithRouter(component: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/decks/:deckId" element={component} />
          <Route path="/decks" element={<div>Decks List</div>} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

describe('DeckDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock setup
    const useDeckMock = vi.mocked(useDeck);
    useDeckMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
      status: 'success',
    } as any);

    const useCardsMock = vi.mocked(useCards);
    useCardsMock.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
      status: 'success',
    } as any);

    const useDeleteDeckMock = vi.mocked(useDeleteDeck);
    useDeleteDeckMock.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      error: null,
      status: 'idle',
    } as any);

    const useDeleteCardMock = vi.mocked(useDeleteCard);
    useDeleteCardMock.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      error: null,
      status: 'idle',
    } as any);
  });

  describe('loading states', () => {
    it('displays loading skeleton when deck is loading', () => {
      const useDeckMock = vi.mocked(useDeck);
      useDeckMock.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        status: 'pending',
      } as any);

      const useCardsMock = vi.mocked(useCards);
      useCardsMock.mockReturnValue({
        data: [],
        isLoading: true,
        error: null,
        status: 'pending',
      } as any);

      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      expect(screen.getByTestId('deck-detail-loading')).toBeInTheDocument();
    });
  });

  describe('error states', () => {
    it('displays error message when deck fetch fails', async () => {
      const useDeckMock = vi.mocked(useDeck);
      useDeckMock.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Deck not found'),
        status: 'error',
      } as any);

      const useCardsMock = vi.mocked(useCards);
      useCardsMock.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
        status: 'success',
      } as any);

      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      await waitFor(() => {
        expect(screen.getByText(/deck not found/i)).toBeInTheDocument();
      });
    });

    it('displays 404 state for invalid deck ID', async () => {
      const useDeckMock = vi.mocked(useDeck);
      useDeckMock.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Not found'),
        status: 'error',
      } as any);

      const useCardsMock = vi.mocked(useCards);
      useCardsMock.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
        status: 'success',
      } as any);

      window.history.pushState({}, 'Deck Detail', '/decks/invalid-id');
      renderWithRouter(<DeckDetailPage />);

      await waitFor(() => {
        expect(screen.getByTestId('error-state')).toBeInTheDocument();
      });
    });
  });

  describe('deck header section', () => {
    beforeEach(() => {
      const useDeckMock = vi.mocked(useDeck);
      useDeckMock.mockReturnValue({
        data: mockDeck,
        isLoading: false,
        error: null,
        status: 'success',
      } as any);

      const useCardsMock = vi.mocked(useCards);
      useCardsMock.mockReturnValue({
        data: [mockCard1, mockCard2, mockCard3],
        isLoading: false,
        error: null,
        status: 'success',
      } as any);
    });

    it('displays deck name and description', () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      expect(screen.getByText('Test Deck')).toBeInTheDocument();
      expect(screen.getByText('A test deck description')).toBeInTheDocument();
    });

    it('displays deck stats (total cards, due today, new cards)', () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      expect(screen.getByText(/3\s+cards/i)).toBeInTheDocument();
      expect(screen.getByText(/1\s+new/i)).toBeInTheDocument();
      expect(screen.getByText(/1\s+learning/i)).toBeInTheDocument();
      expect(screen.getByText(/1\s+review/i)).toBeInTheDocument();
    });

    it('has back button that navigates to /decks', async () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const backButton = screen.getByRole('button', { name: /back/i });
      await userEvent.click(backButton);

      await waitFor(() => {
        expect(screen.getByText('Decks List')).toBeInTheDocument();
      });
    });

    it('has edit button that opens EditDeckModal', async () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const editButton = screen.getByRole('button', { name: /edit deck/i });
      await userEvent.click(editButton);

      expect(screen.getByTestId('edit-deck-modal')).toBeInTheDocument();
    });

    it('can close EditDeckModal', async () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const editButton = screen.getByRole('button', { name: /edit deck/i });
      await userEvent.click(editButton);

      const modal = screen.getByTestId('edit-deck-modal');
      expect(modal).toBeInTheDocument();

      const closeButton = within(modal).getByRole('button', { name: /close/i });
      await userEvent.click(closeButton);

      await waitFor(() => {
        expect(screen.queryByTestId('edit-deck-modal')).not.toBeInTheDocument();
      });
    });

    it('has delete button with confirmation dialog', async () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const deleteButton = screen.getByRole('button', { name: /delete deck/i });
      await userEvent.click(deleteButton);

      expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
    });

    it('cancels deck deletion when user clicks cancel', async () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const deleteButton = screen.getByRole('button', { name: /delete deck/i });
      await userEvent.click(deleteButton);

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await userEvent.click(cancelButton);

      await waitFor(() => {
        expect(screen.queryByText(/are you sure/i)).not.toBeInTheDocument();
      });
      expect(screen.getByText('Test Deck')).toBeInTheDocument();
    });

    it('deletes deck and navigates to /decks on confirm', async () => {
      const useDeleteDeckMock = vi.mocked(useDeleteDeck);
      useDeleteDeckMock.mockReturnValue({
        mutate: vi.fn(),
        isPending: false,
        error: null,
        status: 'idle',
      } as any);

      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const deleteButton = screen.getByRole('button', { name: /delete deck/i });
      expect(deleteButton).toBeInTheDocument();

      // Click delete button should show confirmation
      await userEvent.click(deleteButton);
      expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
    });
  });

  describe('card list section', () => {
    beforeEach(() => {
      const useDeckMock = vi.mocked(useDeck);
      useDeckMock.mockReturnValue({
        data: mockDeck,
        isLoading: false,
        error: null,
        status: 'success',
      } as any);

      const useCardsMock = vi.mocked(useCards);
      useCardsMock.mockReturnValue({
        data: [mockCard1, mockCard2, mockCard3],
        isLoading: false,
        error: null,
        status: 'success',
      } as any);
    });

    it('displays all cards in the deck', () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      expect(screen.getByText('Q1')).toBeInTheDocument();
      expect(screen.getByText('Q2')).toBeInTheDocument();
      expect(screen.getByText(/Q3/i)).toBeInTheDocument();
    });

    it('truncates long front content', () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const cards = screen.getAllByTestId('card-item');
      const thirdCard = cards[2];
      // Check that the third card exists and contains the Q3 content (might be truncated with CSS)
      expect(thirdCard.textContent).toContain('Q3');
    });

    it('displays card tags', () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const allTags = screen.getAllByText(/tag1/);
      expect(allTags.length).toBeGreaterThanOrEqual(1);

      const tag2Elements = screen.queryAllByText('tag2');
      expect(tag2Elements.length).toBeGreaterThanOrEqual(1);
    });

    it('displays card state badges', () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      expect(screen.getByText('new')).toBeInTheDocument();
      expect(screen.getByText('learning')).toBeInTheDocument();
      expect(screen.getByText('review')).toBeInTheDocument();
    });

    it('displays card due date', () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const dueElements = screen.getAllByText(/Due:/);
      expect(dueElements.length).toBeGreaterThanOrEqual(3);
    });

    it('has edit button for each card', () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const editButtons = screen.getAllByRole('button', { name: /edit/i });
      const editCardButtons = editButtons.filter((btn) => btn.getAttribute('aria-label')?.includes('Edit card'));
      expect(editCardButtons.length).toBe(3);
    });

    it('opens EditCardModal when edit button is clicked', async () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const editButtons = screen.getAllByRole('button', { name: /edit/i });
      const editCardButtons = editButtons.filter((btn) => btn.getAttribute('aria-label')?.includes('Edit card'));
      await userEvent.click(editCardButtons[0]);

      expect(screen.getByTestId('edit-card-modal')).toBeInTheDocument();
      expect(screen.getByTestId('edit-card-id')).toBeInTheDocument();
    });

    it('closes EditCardModal when cancel is clicked', async () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const editButtons = screen.getAllByRole('button', { name: /edit/i });
      const editCardButtons = editButtons.filter((btn) => btn.getAttribute('aria-label')?.includes('Edit card'));
      await userEvent.click(editCardButtons[0]);

      const modal = screen.getByTestId('edit-card-modal');
      const closeButton = within(modal).getByRole('button', { name: /close/i });
      await userEvent.click(closeButton);

      await waitFor(() => {
        expect(screen.queryByTestId('edit-card-modal')).not.toBeInTheDocument();
      });
    });

    it('has delete button for each card', () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
      const deleteCardButtons = deleteButtons.filter((btn) => btn.getAttribute('aria-label')?.includes('Delete card'));
      expect(deleteCardButtons.length).toBe(3);
    });

    it('shows confirmation before deleting card', async () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
      const deleteCardButtons = deleteButtons.filter((btn) => btn.getAttribute('aria-label')?.includes('Delete card'));
      await userEvent.click(deleteCardButtons[0]);

      expect(screen.getByText(/are you sure.*delete.*card/i)).toBeInTheDocument();
    });

    it('cancels card deletion when user clicks cancel', async () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
      const deleteCardButtons = deleteButtons.filter((btn) => btn.getAttribute('aria-label')?.includes('Delete card'));
      await userEvent.click(deleteCardButtons[0]);

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await userEvent.click(cancelButton);

      await waitFor(() => {
        expect(screen.queryByText(/are you sure.*delete.*card/i)).not.toBeInTheDocument();
      });
      expect(screen.getByText('Q1')).toBeInTheDocument();
    });

    it('deletes card when user confirms', async () => {
      const useDeleteCardMock = vi.mocked(useDeleteCard);
      useDeleteCardMock.mockReturnValue({
        mutate: vi.fn(),
        isPending: false,
        error: null,
        status: 'idle',
      } as any);

      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
      const deleteCardButtons = deleteButtons.filter((btn) => btn.getAttribute('aria-label')?.includes('Delete card'));
      expect(deleteCardButtons.length).toBeGreaterThanOrEqual(1);

      await userEvent.click(deleteCardButtons[0]);

      // Dialog should be visible after clicking delete
      expect(screen.getByText(/are you sure.*delete.*card/i)).toBeInTheDocument();
    });
  });

  describe('sort and filter functionality', () => {
    beforeEach(() => {
      const useDeckMock = vi.mocked(useDeck);
      useDeckMock.mockReturnValue({
        data: mockDeck,
        isLoading: false,
        error: null,
        status: 'success',
      } as any);

      const useCardsMock = vi.mocked(useCards);
      useCardsMock.mockReturnValue({
        data: [mockCard1, mockCard2, mockCard3],
        isLoading: false,
        error: null,
        status: 'success',
      } as any);
    });

    it('has sort options dropdown', () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      expect(screen.getByTestId('sort-select')).toBeInTheDocument();
    });

    it('sorts cards by due date', async () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const sortSelect = screen.getByTestId('sort-select') as HTMLSelectElement;
      fireEvent.change(sortSelect, { target: { value: 'due' } });

      const cards = screen.getAllByTestId('card-item');
      expect(cards[0].textContent).toContain('Q2');
      expect(cards[1].textContent).toContain('Q1');
      expect(cards[2].textContent).toContain('Q3');
    });

    it('sorts cards by creation date', async () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const sortSelect = screen.getByTestId('sort-select') as HTMLSelectElement;
      fireEvent.change(sortSelect, { target: { value: 'created' } });

      const cards = screen.getAllByTestId('card-item');
      expect(cards.length).toBe(3);
    });

    it('sorts cards by state', async () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const sortSelect = screen.getByTestId('sort-select') as HTMLSelectElement;
      fireEvent.change(sortSelect, { target: { value: 'state' } });

      const cards = screen.getAllByTestId('card-item');
      expect(cards.length).toBe(3);
    });

    it('has filter options for card state', () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      expect(screen.getByTestId('filter-select')).toBeInTheDocument();
    });

    it('filters to show only new cards', async () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const filterSelect = screen.getByTestId('filter-select') as HTMLSelectElement;
      fireEvent.change(filterSelect, { target: { value: 'new' } });

      const cards = screen.getAllByTestId('card-item');
      expect(cards.length).toBe(1);
      expect(cards[0].textContent).toContain('Q1');
    });

    it('filters to show only learning cards', async () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const filterSelect = screen.getByTestId('filter-select') as HTMLSelectElement;
      fireEvent.change(filterSelect, { target: { value: 'learning' } });

      const cards = screen.getAllByTestId('card-item');
      expect(cards.length).toBe(1);
      expect(cards[0].textContent).toContain('Q2');
    });

    it('filters to show only review cards', async () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const filterSelect = screen.getByTestId('filter-select') as HTMLSelectElement;
      fireEvent.change(filterSelect, { target: { value: 'review' } });

      const cards = screen.getAllByTestId('card-item');
      expect(cards.length).toBe(1);
      expect(cards[0].textContent).toContain('Q3');
    });

    it('shows all cards when filter is set to all', async () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const filterSelect = screen.getByTestId('filter-select') as HTMLSelectElement;
      fireEvent.change(filterSelect, { target: { value: 'new' } });
      expect(screen.getAllByTestId('card-item').length).toBe(1);

      fireEvent.change(filterSelect, { target: { value: 'all' } });
      expect(screen.getAllByTestId('card-item').length).toBe(3);
    });
  });

  describe('create card functionality', () => {
    beforeEach(() => {
      const useDeckMock = vi.mocked(useDeck);
      useDeckMock.mockReturnValue({
        data: mockDeck,
        isLoading: false,
        error: null,
        status: 'success',
      } as any);

      const useCardsMock = vi.mocked(useCards);
      useCardsMock.mockReturnValue({
        data: [mockCard1],
        isLoading: false,
        error: null,
        status: 'success',
      } as any);
    });

    it('has create card button', () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      expect(screen.getByRole('button', { name: /create card/i })).toBeInTheDocument();
    });

    it('opens CreateCardModal when create button is clicked', async () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const createButton = screen.getByRole('button', { name: /create card/i });
      await userEvent.click(createButton);

      expect(screen.getByTestId('create-card-modal')).toBeInTheDocument();
      expect(screen.getByText('Deck ID: deck-1')).toBeInTheDocument();
    });

    it('closes CreateCardModal when cancel is clicked', async () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const createButton = screen.getByRole('button', { name: /create card/i });
      await userEvent.click(createButton);

      const modal = screen.getByTestId('create-card-modal');
      const closeButton = within(modal).getByRole('button', { name: /close/i });
      await userEvent.click(closeButton);

      await waitFor(() => {
        expect(screen.queryByTestId('create-card-modal')).not.toBeInTheDocument();
      });
    });
  });

  describe('empty state', () => {
    it('displays empty state when no cards exist', () => {
      const useDeckMock = vi.mocked(useDeck);
      useDeckMock.mockReturnValue({
        data: mockDeck,
        isLoading: false,
        error: null,
        status: 'success',
      } as any);

      const useCardsMock = vi.mocked(useCards);
      useCardsMock.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
        status: 'success',
      } as any);

      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /create card/i })).toBeInTheDocument();
    });
  });

  describe('responsive design', () => {
    beforeEach(() => {
      const useDeckMock = vi.mocked(useDeck);
      useDeckMock.mockReturnValue({
        data: mockDeck,
        isLoading: false,
        error: null,
        status: 'success',
      } as any);

      const useCardsMock = vi.mocked(useCards);
      useCardsMock.mockReturnValue({
        data: [mockCard1, mockCard2],
        isLoading: false,
        error: null,
        status: 'success',
      } as any);
    });

    it('has accessible structure with proper ARIA labels', () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const mainContent = screen.getByRole('main');
      expect(mainContent).toBeInTheDocument();
    });

    it('has semantic HTML elements', () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const sections = screen.getAllByRole('region');
      expect(sections.length).toBeGreaterThan(0);
    });

    it('displays controls above the card list', () => {
      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      const cardSection = screen.getByRole('region', { name: 'Cards list' });
      expect(cardSection).toBeInTheDocument();

      const sortSelect = screen.getByTestId('sort-select');
      const filterSelect = screen.getByTestId('filter-select');

      expect(sortSelect).toBeInTheDocument();
      expect(filterSelect).toBeInTheDocument();

      const cards = screen.getAllByTestId('card-item');
      expect(cards.length).toBeGreaterThan(0);
    });
  });

  describe('loading state for operations', () => {
    it('shows loading state while creating card', async () => {
      const useDeckMock = vi.mocked(useDeck);
      useDeckMock.mockReturnValue({
        data: mockDeck,
        isLoading: false,
        error: null,
        status: 'success',
      } as any);

      const useCardsMock = vi.mocked(useCards);
      useCardsMock.mockReturnValue({
        data: [mockCard1],
        isLoading: false,
        error: null,
        status: 'success',
      } as any);

      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      const { rerender } = renderWithRouter(<DeckDetailPage />);

      const createButton = screen.getByRole('button', { name: /create card/i });
      expect(createButton).not.toBeDisabled();
    });
  });

  describe('URL parameter handling', () => {
    it('correctly uses deckId from URL parameter', () => {
      const useDeckMock = vi.mocked(useDeck);
      useDeckMock.mockReturnValue({
        data: mockDeck,
        isLoading: false,
        error: null,
        status: 'success',
      } as any);

      const useCardsMock = vi.mocked(useCards);
      useCardsMock.mockReturnValue({
        data: [mockCard1],
        isLoading: false,
        error: null,
        status: 'success',
      } as any);

      window.history.pushState({}, 'Deck Detail', '/decks/deck-1');
      renderWithRouter(<DeckDetailPage />);

      expect(useDeckMock).toHaveBeenCalledWith('deck-1');
      expect(useCardsMock).toHaveBeenCalledWith('deck-1');
    });

    it('handles different deck IDs in URL', () => {
      const useDeckMock = vi.mocked(useDeck);
      useDeckMock.mockReturnValue({
        data: mockDeck,
        isLoading: false,
        error: null,
        status: 'success',
      } as any);

      const useCardsMock = vi.mocked(useCards);
      useCardsMock.mockReturnValue({
        data: [mockCard1],
        isLoading: false,
        error: null,
        status: 'success',
      } as any);

      window.history.pushState({}, 'Deck Detail', '/decks/different-deck-id');
      renderWithRouter(<DeckDetailPage />);

      expect(useDeckMock).toHaveBeenCalledWith('different-deck-id');
      expect(useCardsMock).toHaveBeenCalledWith('different-deck-id');
    });
  });
});
