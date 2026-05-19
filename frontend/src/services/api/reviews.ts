/**
 * Review API endpoints.
 */

import { AxiosInstance } from 'axios';
import { ReviewLog, CreateReviewPayload } from '@/types';
import { handleApiCall } from './client';

/**
 * Constants for review API
 */
const DEFAULT_REVIEW_HISTORY_LIMIT = 10;

/**
 * Provides review-related API methods.
 */
export function createReviewsApi(apiClient: AxiosInstance) {
  return {
    /**
     * Submit a review for a card.
     */
    async createReview(payload: CreateReviewPayload): Promise<ReviewLog> {
      return handleApiCall(() => apiClient.post('/reviews', payload), 'Failed to submit review');
    },

    /**
     * Get review history for a card.
     */
    async getReviewHistory(
      cardId: string,
      limit: number = DEFAULT_REVIEW_HISTORY_LIMIT,
    ): Promise<ReviewLog[]> {
      return handleApiCall(
        () =>
          apiClient.get(`/cards/${cardId}/reviews`, {
            params: { limit },
          }),
        `Failed to fetch review history for card ${cardId}`,
      );
    },
  };
}
