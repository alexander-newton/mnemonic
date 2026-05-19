/**
 * React Query hooks for card operations.
 * Manages querying, creating, updating, and deleting cards with cache invalidation.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryResult,
  UseMutationResult,
} from '@tanstack/react-query';
import { api } from '../services/api';
import type { Card, CreateCardPayload, UpdateCardPayload } from '../types';

/**
 * Query key factory for card-related queries.
 * Ensures consistent cache management across hooks.
 */
const cardKeys = {
  all: ['cards'] as const,
  lists: () => [...cardKeys.all, 'list'] as const,
  listByDeck: (deckId: string) => [...cardKeys.lists(), 'deck', deckId] as const,
  detail: (id: string) => [...cardKeys.all, 'detail', id] as const,
};

/**
 * Hook to fetch all cards in a specific deck.
 * Only enabled when deck ID is provided.
 *
 * @param deckId - The deck ID to fetch cards from (if empty/null, query is disabled)
 * @returns Query result with cards array and loading/error state
 *
 * @example
 * ```tsx
 * const { data: cards, isLoading, error } = useCards(deckId);
 *
 * if (isLoading) return <Skeleton />;
 * if (error) return <div>Error: {error.message}</div>;
 *
 * return (
 *   <ul>
 *     {cards.map(card => (
 *       <CardItem key={card.id} card={card} />
 *     ))}
 *   </ul>
 * );
 * ```
 */
export function useCards(deckId?: string): UseQueryResult<Card[], Error> {
  return useQuery({
    queryKey: deckId ? cardKeys.listByDeck(deckId) : [],
    queryFn: () => {
      if (!deckId) throw new Error('Deck ID is required');
      return api.getCards(deckId);
    },
    enabled: !!deckId,
    staleTime: 3 * 60 * 1000, // 3 minutes
  });
}

/**
 * Hook to fetch a specific card by ID.
 * Only enabled when card ID is provided.
 *
 * @param id - The card ID to fetch (if empty/null, query is disabled)
 * @returns Query result with card and loading/error state
 *
 * @example
 * ```tsx
 * const { data: card, isLoading } = useCard(cardId);
 *
 * if (isLoading) return <Skeleton />;
 *
 * return <CardDisplay card={card} />;
 * ```
 */
export function useCard(id?: string): UseQueryResult<Card, Error> {
  return useQuery({
    queryKey: id ? cardKeys.detail(id) : [],
    queryFn: () => {
      if (!id) throw new Error('Card ID is required');
      return api.getCard(id);
    },
    enabled: !!id,
    staleTime: 3 * 60 * 1000, // 3 minutes
  });
}

/**
 * Hook to create a new card.
 * Invalidates the deck's card list cache on success.
 *
 * @returns Mutation result with mutate function and status
 *
 * @example
 * ```tsx
 * const { mutate: createCard, isPending, error } = useCreateCard();
 *
 * const handleCreate = (payload: CreateCardPayload) => {
 *   createCard(payload, {
 *     onSuccess: () => {
 *       toast.success('Card created!');
 *     },
 *   });
 * };
 * ```
 */
export function useCreateCard(): UseMutationResult<Card, Error, CreateCardPayload, unknown> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateCardPayload) => api.createCard(data),
    onSuccess: (newCard) => {
      // Invalidate the deck's card list to refetch
      queryClient.invalidateQueries({
        queryKey: cardKeys.listByDeck(newCard.deckId),
      });
    },
  });
}

/**
 * Hook to update an existing card.
 * Invalidates the card's detail cache and the deck's card list cache.
 *
 * @returns Mutation result with mutate function and status
 *
 * @example
 * ```tsx
 * const { mutate: updateCard, isPending } = useUpdateCard();
 *
 * const handleUpdate = (id: string, payload: UpdateCardPayload) => {
 *   updateCard({ id, data: payload });
 * };
 * ```
 */
export function useUpdateCard(): UseMutationResult<
  Card,
  Error,
  { id: string; data: UpdateCardPayload },
  unknown
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) => api.updateCard(id, data),
    onSuccess: (updatedCard) => {
      // Invalidate card detail and deck's card list
      queryClient.invalidateQueries({
        queryKey: cardKeys.detail(updatedCard.id),
      });
      queryClient.invalidateQueries({
        queryKey: cardKeys.listByDeck(updatedCard.deckId),
      });
    },
  });
}

/**
 * Hook to delete a card.
 * Invalidates the card's detail cache and the deck's card list cache.
 *
 * @returns Mutation result with mutate function and status
 *
 * @example
 * ```tsx
 * const { mutate: deleteCard, isPending } = useDeleteCard();
 *
 * const handleDelete = (id: string, deckId: string) => {
 *   if (confirm('Delete this card?')) {
 *     deleteCard({ id, deckId });
 *   }
 * };
 * ```
 */
export function useDeleteCard(): UseMutationResult<
  void,
  Error,
  { id: string; deckId: string },
  unknown
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id }) => api.deleteCard(id),
    onSuccess: (_, { id, deckId }) => {
      // Invalidate card detail and deck's card list
      queryClient.invalidateQueries({ queryKey: cardKeys.detail(id) });
      queryClient.invalidateQueries({
        queryKey: cardKeys.listByDeck(deckId),
      });
    },
  });
}
