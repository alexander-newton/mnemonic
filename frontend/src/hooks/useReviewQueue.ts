/** React Query hook for a deck's review queue. */

import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { api } from '../services/api';
import type { QueueResponse } from '../types';

export function useReviewQueue(deck?: string): UseQueryResult<QueueResponse, Error> {
  return useQuery({
    queryKey: ['review-queue', deck],
    queryFn: () => {
      if (!deck) throw new Error('Deck is required');
      return api.reviewQueue(deck);
    },
    enabled: !!deck,
    staleTime: 0,
  });
}
