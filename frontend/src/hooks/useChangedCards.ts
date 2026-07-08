/**
 * React Query hooks for the "review changed cards" panel.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryResult,
  UseMutationResult,
} from '@tanstack/react-query';
import { api } from '../services/api';
import type { ChangedCard, CoreChangeDecision, SchedulingSnapshot } from '../types';

const changedKeys = {
  all: ['changed-cards'] as const,
};

/**
 * Fetch all cards whose core content changed since scheduling was set.
 *
 * @returns Query result with changed cards array and loading/error state
 *
 * @example
 * ```tsx
 * const { data: changedCards, isLoading, error } = useChangedCards();
 *
 * if (isLoading) return <Skeleton />;
 * if (error) return <div>Error: {error.message}</div>;
 *
 * return (
 *   <ul>
 *     {changedCards.map(card => (
 *       <ChangedCardItem key={card.card_id} card={card} />
 *     ))}
 *   </ul>
 * );
 * ```
 */
export function useChangedCards(): UseQueryResult<ChangedCard[], Error> {
  return useQuery({
    queryKey: changedKeys.all,
    queryFn: () => api.listChangedCards(),
    staleTime: 60 * 1000,
  });
}

/**
 * Apply keep / soft-reset / full-reset decision to a card with changed core content.
 * Refreshes the changed-cards list on success.
 *
 * @returns Mutation result with mutate function and status
 *
 * @example
 * ```tsx
 * const { mutate: applyCoreChange, isPending, error } = useApplyCoreChange();
 *
 * const handleResolveChange = (cardId: string, decision: CoreChangeDecision) => {
 *   applyCoreChange({ cardId, decision }, {
 *     onSuccess: () => {
 *       toast.success('Change applied!');
 *     },
 *   });
 * };
 * ```
 */
export function useApplyCoreChange(): UseMutationResult<
  SchedulingSnapshot,
  Error,
  { cardId: string; decision: CoreChangeDecision },
  unknown
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ cardId, decision }) => api.applyCoreChange(cardId, decision),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: changedKeys.all });
    },
  });
}
