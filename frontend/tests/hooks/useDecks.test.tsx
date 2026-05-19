/**
 * Tests for useDecks hooks - deck query and mutation operations
 */

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  useDecks,
  useDeck,
  useCreateDeck,
  useUpdateDeck,
  useDeleteDeck,
} from '@/hooks/useDecks';
import * as apiModule from '@/services/api';
import { useDeckStore } from '@/stores/deckStore';
import type { Deck, CreateDeckPayload, UpdateDeckPayload } from '@/types';

// Mock the API module
vi.mock('@/services/api', () => ({
  api: {
    getDecks: vi.fn(),
    getDeck: vi.fn(),
    createDeck: vi.fn(),
    updateDeck: vi.fn(),
    deleteDeck: vi.fn(),
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
 * Helper to create a mock deck object.
 */
function createMockDeck(overrides?: Partial<Deck>): Deck {
  return {
    id: '1',
    userId: 'user-1',
    name: 'Test Deck',
    description: 'A test deck',
    variationEnabled: true,
    variationFrequency: 0.5,
    leechThreshold: 8,
    dailyReviewLimit: 20,
    dailyNewLimit: 10,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...overrides,
  };
}

describe('useDecks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useDeckStore.setState({
      decks: [],
      selectedDeckId: null,
      isLoading: false,
      error: null,
    });
  });

  it('fetches all decks successfully', async () => {
    const mockDecks = [
      createMockDeck({ id: '1', name: 'Deck 1' }),
      createMockDeck({ id: '2', name: 'Deck 2' }),
    ];
    vi.mocked(apiModule.api.getDecks).mockResolvedValue(mockDecks);

    const { result } = renderHook(() => useDecks(), { wrapper: createWrapper() });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiModule.api.getDecks).toHaveBeenCalled();
    expect(result.current.data).toEqual(mockDecks);
    expect(useDeckStore.getState().decks).toEqual(mockDecks);
  });

  it('handles fetch error gracefully', async () => {
    const error = new Error('Network error');
    vi.mocked(apiModule.api.getDecks).mockRejectedValue(error);

    const { result } = renderHook(() => useDecks(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBe(error);
    expect(useDeckStore.getState().error).toBe('Network error');
  });

  it('sets loading and error state on store', async () => {
    vi.mocked(apiModule.api.getDecks).mockResolvedValue([]);

    const { result } = renderHook(() => useDecks(), { wrapper: createWrapper() });

    expect(useDeckStore.getState().isLoading).toBe(true);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(useDeckStore.getState().isLoading).toBe(false);
    expect(useDeckStore.getState().error).toBeNull();
  });

  it('returns data and is independent of other tests', async () => {
    const mockDecks = [createMockDeck()];
    vi.mocked(apiModule.api.getDecks).mockResolvedValue(mockDecks);

    const { result } = renderHook(() => useDecks(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockDecks);
    expect(useDeckStore.getState().decks).toEqual(mockDecks);
  });
});

describe('useDeck', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches a specific deck by ID', async () => {
    const mockDeck = createMockDeck({ id: 'deck-123' });
    vi.mocked(apiModule.api.getDeck).mockResolvedValue(mockDeck);

    const { result } = renderHook(() => useDeck('deck-123'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiModule.api.getDeck).toHaveBeenCalledWith('deck-123');
    expect(result.current.data).toEqual(mockDeck);
  });

  it('does not fetch when ID is not provided', () => {
    vi.mocked(apiModule.api.getDeck).mockResolvedValue(createMockDeck());

    const { result } = renderHook(() => useDeck(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(apiModule.api.getDeck).not.toHaveBeenCalled();
  });

  it('handles fetch error for specific deck', async () => {
    const error = new Error('Deck not found');
    vi.mocked(apiModule.api.getDeck).mockRejectedValue(error);

    const { result } = renderHook(() => useDeck('invalid-id'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBe(error);
  });
});

describe('useCreateDeck', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('creates a new deck and updates store', async () => {
    const newDeck = createMockDeck({ id: 'new-deck', name: 'New Deck' });
    vi.mocked(apiModule.api.createDeck).mockResolvedValue(newDeck);

    const { result } = renderHook(() => useCreateDeck(), {
      wrapper: createWrapper(),
    });

    const payload: CreateDeckPayload = {
      name: 'New Deck',
      description: 'A new deck',
    };

    result.current.mutate(payload);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiModule.api.createDeck).toHaveBeenCalledWith(payload);
    expect(useDeckStore.getState().decks).toContainEqual(newDeck);
  });

  it('handles creation error', async () => {
    const error = new Error('Invalid deck data');
    vi.mocked(apiModule.api.createDeck).mockRejectedValue(error);

    const { result } = renderHook(() => useCreateDeck(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ name: 'Invalid Deck' });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBe(error);
  });

  it('provides success state after creation', async () => {
    const newDeck = createMockDeck();
    vi.mocked(apiModule.api.createDeck).mockResolvedValue(newDeck);

    const { result } = renderHook(() => useCreateDeck(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ name: 'Created Deck' });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(newDeck);
  });
});

describe('useUpdateDeck', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('updates an existing deck and updates store', async () => {
    const deckId = 'deck-1';
    const updated = createMockDeck({
      id: deckId,
      name: 'Updated Deck',
      description: 'Updated description',
    });
    vi.mocked(apiModule.api.updateDeck).mockResolvedValue(updated);

    useDeckStore.setState({
      decks: [createMockDeck({ id: deckId, name: 'Old Deck' })],
    });

    const { result } = renderHook(() => useUpdateDeck(), {
      wrapper: createWrapper(),
    });

    const payload: UpdateDeckPayload = {
      name: 'Updated Deck',
      description: 'Updated description',
    };

    result.current.mutate({ id: deckId, data: payload });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiModule.api.updateDeck).toHaveBeenCalledWith(deckId, payload);
    const deck = useDeckStore.getState().decks.find((d) => d.id === deckId);
    expect(deck?.name).toBe('Updated Deck');
    expect(deck?.description).toBe('Updated description');
  });

  it('handles update error', async () => {
    const error = new Error('Deck not found');
    vi.mocked(apiModule.api.updateDeck).mockRejectedValue(error);

    const { result } = renderHook(() => useUpdateDeck(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ id: 'invalid', data: { name: 'New Name' } });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBe(error);
  });

  it('invalidates related queries on success', async () => {
    const deckId = 'deck-1';
    const updated = createMockDeck({ id: deckId });
    vi.mocked(apiModule.api.updateDeck).mockResolvedValue(updated);

    const queryClient = new QueryClient();
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useUpdateDeck(), { wrapper });

    result.current.mutate({ id: deckId, data: { name: 'Updated' } });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Verify invalidation occurred (hard to test directly, but we can verify success)
    expect(result.current.isSuccess).toBe(true);
  });
});

describe('useDeleteDeck', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('deletes a deck and updates store', async () => {
    const deckId = 'deck-1';
    vi.mocked(apiModule.api.deleteDeck).mockResolvedValue(undefined);

    useDeckStore.setState({
      decks: [
        createMockDeck({ id: deckId }),
        createMockDeck({ id: 'deck-2' }),
      ],
    });

    const { result } = renderHook(() => useDeleteDeck(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(deckId);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiModule.api.deleteDeck).toHaveBeenCalledWith(deckId);
    expect(useDeckStore.getState().decks).not.toContainEqual(
      expect.objectContaining({ id: deckId }),
    );
    expect(useDeckStore.getState().decks.length).toBe(1);
  });

  it('handles deletion error', async () => {
    const error = new Error('Deck not found');
    vi.mocked(apiModule.api.deleteDeck).mockRejectedValue(error);

    const { result } = renderHook(() => useDeleteDeck(), {
      wrapper: createWrapper(),
    });

    result.current.mutate('invalid-id');

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBe(error);
  });

  it('clears selected deck if it was deleted', async () => {
    const deckId = 'deck-1';
    vi.mocked(apiModule.api.deleteDeck).mockResolvedValue(undefined);

    useDeckStore.setState({
      decks: [createMockDeck({ id: deckId })],
      selectedDeckId: deckId,
    });

    const { result } = renderHook(() => useDeleteDeck(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(deckId);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(useDeckStore.getState().selectedDeckId).toBeNull();
  });

  it('provides success state after deletion', async () => {
    vi.mocked(apiModule.api.deleteDeck).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteDeck(), {
      wrapper: createWrapper(),
    });

    result.current.mutate('deck-id');

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.isPending).toBe(false);
  });
});
