/**
 * React Query hooks for deck operations.
 * Manages querying, creating, updating, and deleting decks with cache invalidation.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryResult,
  UseMutationResult,
} from '@tanstack/react-query';
import { useDeckStore } from '../stores';
import { api } from '../services/api';
import type { Deck, CreateDeckPayload, UpdateDeckPayload } from '../types';

/**
 * Query key factory for deck-related queries.
 * Ensures consistent cache management across hooks.
 */
const deckKeys = {
  all: ['decks'] as const,
  lists: () => [...deckKeys.all, 'list'] as const,
  detail: (id: string) => [...deckKeys.all, 'detail', id] as const,
};

/**
 * Hook to fetch all decks for the current user.
 * Automatically syncs data to Zustand store.
 *
 * @returns Query result with decks array and loading/error state
 *
 * @example
 * ```tsx
 * const { data: decks, isLoading, error } = useDecks();
 *
 * if (isLoading) return <div>Loading decks...</div>;
 * if (error) return <div>Error: {error.message}</div>;
 *
 * return (
 *   <div>
 *     {decks.map(deck => (
 *       <DeckCard key={deck.id} deck={deck} />
 *     ))}
 *   </div>
 * );
 * ```
 */
export function useDecks(): UseQueryResult<Deck[], Error> {
  const setDecks = useDeckStore((state) => state.setDecks);
  const setLoading = useDeckStore((state) => state.setLoading);
  const setError = useDeckStore((state) => state.setError);

  return useQuery({
    queryKey: deckKeys.lists(),
    queryFn: async () => {
      setLoading(true);
      try {
        const data = await api.getDecks();
        setDecks(data);
        setLoading(false);
        return data;
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to fetch decks';
        setError(message);
        throw error;
      }
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to fetch a specific deck by ID.
 * Only enabled when deck ID is provided.
 *
 * @param id - The deck ID to fetch (if empty/null, query is disabled)
 * @returns Query result with deck and loading/error state
 *
 * @example
 * ```tsx
 * const { data: deck, isLoading } = useDeck(deckId);
 *
 * if (isLoading) return <Skeleton />;
 *
 * return <DeckForm initialData={deck} />;
 * ```
 */
export function useDeck(id?: string): UseQueryResult<Deck, Error> {
  return useQuery({
    queryKey: id ? deckKeys.detail(id) : [],
    queryFn: () => {
      if (!id) throw new Error('Deck ID is required');
      return api.getDeck(id);
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to create a new deck.
 * Performs optimistic update and invalidates related queries.
 *
 * @returns Mutation result with mutate function and status
 *
 * @example
 * ```tsx
 * const { mutate: createDeck, isPending, error } = useCreateDeck();
 *
 * const handleCreate = (data: CreateDeckPayload) => {
 *   createDeck(data, {
 *     onSuccess: (newDeck) => {
 *       toast.success(`Deck "${newDeck.name}" created!`);
 *     },
 *   });
 * };
 * ```
 */
export function useCreateDeck(): UseMutationResult<Deck, Error, CreateDeckPayload, unknown> {
  const queryClient = useQueryClient();
  const addDeck = useDeckStore((state) => state.addDeck);

  return useMutation({
    mutationFn: (data: CreateDeckPayload) => api.createDeck(data),
    onSuccess: (newDeck) => {
      // Optimistic update to store
      addDeck(newDeck);
      // Invalidate to refetch if needed
      queryClient.invalidateQueries({ queryKey: deckKeys.lists() });
    },
  });
}

/**
 * Hook to update an existing deck.
 * Performs optimistic update and invalidates related queries.
 *
 * @returns Mutation result with mutate function and status
 *
 * @example
 * ```tsx
 * const { mutate: updateDeck, isPending } = useUpdateDeck();
 *
 * const handleUpdate = (id: string, data: UpdateDeckPayload) => {
 *   updateDeck({ id, data });
 * };
 * ```
 */
export function useUpdateDeck(): UseMutationResult<
  Deck,
  Error,
  { id: string; data: UpdateDeckPayload },
  unknown
> {
  const queryClient = useQueryClient();
  const updateDeck = useDeckStore((state) => state.updateDeck);

  return useMutation({
    mutationFn: ({ id, data }) => api.updateDeck(id, data),
    onSuccess: (updatedDeck) => {
      // Optimistic update to store
      updateDeck(updatedDeck.id, updatedDeck);
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: deckKeys.lists() });
      queryClient.invalidateQueries({
        queryKey: deckKeys.detail(updatedDeck.id),
      });
    },
  });
}

/**
 * Hook to delete a deck.
 * Performs optimistic update and invalidates related queries.
 *
 * @returns Mutation result with mutate function and status
 *
 * @example
 * ```tsx
 * const { mutate: deleteDeck, isPending } = useDeleteDeck();
 *
 * const handleDelete = (id: string) => {
 *   if (confirm('Are you sure?')) {
 *     deleteDeck(id);
 *   }
 * };
 * ```
 */
export function useDeleteDeck(): UseMutationResult<void, Error, string, unknown> {
  const queryClient = useQueryClient();
  const removeDeck = useDeckStore((state) => state.removeDeck);

  return useMutation({
    mutationFn: (id: string) => api.deleteDeck(id),
    onSuccess: (_, deletedId) => {
      // Optimistic update to store
      removeDeck(deletedId);
      // Invalidate queries
      queryClient.invalidateQueries({ queryKey: deckKeys.lists() });
      queryClient.invalidateQueries({ queryKey: deckKeys.detail(deletedId) });
    },
  });
}
