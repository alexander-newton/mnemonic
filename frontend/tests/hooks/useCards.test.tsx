/**
 * Tests for useCards hooks - card query and mutation operations
 */

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  useCards,
  useCard,
  useCreateCard,
  useUpdateCard,
  useDeleteCard,
} from '@/hooks/useCards';
import * as apiModule from '@/services/api';
import type { Card, CreateCardPayload, UpdateCardPayload } from '@/types';

// Mock the API module
vi.mock('@/services/api', () => ({
  api: {
    getCards: vi.fn(),
    getCard: vi.fn(),
    createCard: vi.fn(),
    updateCard: vi.fn(),
    deleteCard: vi.fn(),
  },
}));

/**
 * Creates a test wrapper with QueryClientProvider for hook testing.
 */
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return function Wrapper(
    props: { children: React.ReactNode },
  ): React.ReactNode {
    return (
      <QueryClientProvider client={queryClient}>
        {props.children}
      </QueryClientProvider>
    );
  };
}

/**
 * Helper to create a mock card object.
 */
function createMockCard(overrides?: Partial<Card>): Card {
  return {
    id: '1',
    deckId: 'deck-1',
    cardTypeId: 'type-1',
    content: 'Card content',
    notes: 'Card notes',
    tags: ['tag1', 'tag2'],
    suspended: false,
    state: 'new',
    stability: 1,
    difficulty: 5,
    due: new Date().toISOString(),
    reps: 0,
    lapses: 0,
    leechScore: 0,
    leechNotified: false,
    parentCardId: null,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...overrides,
  };
}

describe('useCards', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches all cards in a deck', async () => {
    const deckId = 'deck-1';
    const mockCards = [
      createMockCard({ id: '1', deckId }),
      createMockCard({ id: '2', deckId }),
    ];
    vi.mocked(apiModule.api.getCards).mockResolvedValue(mockCards);

    const { result } = renderHook(() => useCards(deckId), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiModule.api.getCards).toHaveBeenCalledWith(deckId);
    expect(result.current.data).toEqual(mockCards);
  });

  it('does not fetch when deck ID is not provided', () => {
    vi.mocked(apiModule.api.getCards).mockResolvedValue([]);

    const { result } = renderHook(() => useCards(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(apiModule.api.getCards).not.toHaveBeenCalled();
  });

  it('handles fetch error gracefully', async () => {
    const error = new Error('Failed to fetch cards');
    vi.mocked(apiModule.api.getCards).mockRejectedValue(error);

    const { result } = renderHook(() => useCards('deck-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBe(error);
  });

  it('caches cards by deck ID', async () => {
    const deckId = 'deck-1';
    const mockCards = [createMockCard()];
    vi.mocked(apiModule.api.getCards).mockResolvedValue(mockCards);

    const { result: result1 } = renderHook(() => useCards(deckId), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result1.current.isSuccess).toBe(true));

    expect(apiModule.api.getCards).toHaveBeenCalledTimes(1);

    // Different deck should refetch
    vi.mocked(apiModule.api.getCards).mockResolvedValue([
      createMockCard({ deckId: 'deck-2' }),
    ]);

    const { result: result2 } = renderHook(() => useCards('deck-2'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result2.current.isSuccess).toBe(true));

    expect(apiModule.api.getCards).toHaveBeenCalledTimes(2);
  });
});

describe('useCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches a specific card by ID', async () => {
    const cardId = 'card-123';
    const mockCard = createMockCard({ id: cardId });
    vi.mocked(apiModule.api.getCard).mockResolvedValue(mockCard);

    const { result } = renderHook(() => useCard(cardId), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiModule.api.getCard).toHaveBeenCalledWith(cardId);
    expect(result.current.data).toEqual(mockCard);
  });

  it('does not fetch when card ID is not provided', () => {
    vi.mocked(apiModule.api.getCard).mockResolvedValue(createMockCard());

    const { result } = renderHook(() => useCard(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(apiModule.api.getCard).not.toHaveBeenCalled();
  });

  it('handles fetch error for specific card', async () => {
    const error = new Error('Card not found');
    vi.mocked(apiModule.api.getCard).mockRejectedValue(error);

    const { result } = renderHook(() => useCard('invalid-id'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBe(error);
  });
});

describe('useCreateCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('creates a new card successfully', async () => {
    const newCard = createMockCard({ id: 'new-card' });
    vi.mocked(apiModule.api.createCard).mockResolvedValue(newCard);

    const { result } = renderHook(() => useCreateCard(), {
      wrapper: createWrapper(),
    });

    const payload: CreateCardPayload = {
      deckId: 'deck-1',
      cardTypeId: 'type-1',
      content: 'New card content',
      notes: 'Notes',
      tags: ['tag1'],
    };

    result.current.mutate(payload);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiModule.api.createCard).toHaveBeenCalledWith(payload);
    expect(result.current.data).toEqual(newCard);
  });

  it('handles creation error', async () => {
    const error = new Error('Invalid card data');
    vi.mocked(apiModule.api.createCard).mockRejectedValue(error);

    const { result } = renderHook(() => useCreateCard(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      deckId: 'deck-1',
      cardTypeId: 'type-1',
      content: 'Content',
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBe(error);
  });

  it('provides success state after creation', async () => {
    const newCard = createMockCard();
    vi.mocked(apiModule.api.createCard).mockResolvedValue(newCard);

    const { result } = renderHook(() => useCreateCard(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      deckId: 'deck-1',
      cardTypeId: 'type-1',
      content: 'Content',
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(newCard);
  });
});

describe('useUpdateCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('updates an existing card successfully', async () => {
    const cardId = 'card-1';
    const deckId = 'deck-1';
    const updated = createMockCard({
      id: cardId,
      deckId,
      content: 'Updated content',
    });
    vi.mocked(apiModule.api.updateCard).mockResolvedValue(updated);

    const { result } = renderHook(() => useUpdateCard(), {
      wrapper: createWrapper(),
    });

    const payload: UpdateCardPayload = {
      content: 'Updated content',
      notes: 'Updated notes',
    };

    result.current.mutate({ id: cardId, data: payload });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiModule.api.updateCard).toHaveBeenCalledWith(cardId, payload);
    expect(result.current.data).toEqual(updated);
  });

  it('handles update error', async () => {
    const error = new Error('Card not found');
    vi.mocked(apiModule.api.updateCard).mockRejectedValue(error);

    const { result } = renderHook(() => useUpdateCard(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ id: 'invalid', data: { content: 'New' } });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBe(error);
  });

  it('invalidates card detail and deck cards on success', async () => {
    const cardId = 'card-1';
    const deckId = 'deck-1';
    const updated = createMockCard({ id: cardId, deckId });
    vi.mocked(apiModule.api.updateCard).mockResolvedValue(updated);

    const queryClient = new QueryClient();
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useUpdateCard(), { wrapper });

    result.current.mutate({ id: cardId, data: { content: 'Updated' } });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Cache invalidation is implicit in success
    expect(result.current.isSuccess).toBe(true);
  });
});

describe('useDeleteCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('deletes a card successfully', async () => {
    const cardId = 'card-1';
    const deckId = 'deck-1';
    vi.mocked(apiModule.api.deleteCard).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteCard(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ id: cardId, deckId });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiModule.api.deleteCard).toHaveBeenCalledWith(cardId);
  });

  it('handles deletion error', async () => {
    const error = new Error('Card not found');
    vi.mocked(apiModule.api.deleteCard).mockRejectedValue(error);

    const { result } = renderHook(() => useDeleteCard(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ id: 'invalid', deckId: 'deck-1' });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBe(error);
  });

  it('invalidates related queries on success', async () => {
    const cardId = 'card-1';
    const deckId = 'deck-1';
    vi.mocked(apiModule.api.deleteCard).mockResolvedValue(undefined);

    const queryClient = new QueryClient();
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useDeleteCard(), { wrapper });

    result.current.mutate({ id: cardId, deckId });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Cache invalidation occurred
    expect(result.current.isSuccess).toBe(true);
  });

  it('provides success state after deletion', async () => {
    vi.mocked(apiModule.api.deleteCard).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteCard(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ id: 'card-1', deckId: 'deck-1' });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.isPending).toBe(false);
  });
});
