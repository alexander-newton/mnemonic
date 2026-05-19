/**
 * Card management API endpoints.
 */

import { AxiosInstance } from 'axios';
import { Card, CreateCardPayload, UpdateCardPayload } from '@/types';
import { handleApiCall } from './client';

/**
 * Provides card-related API methods.
 */
export function createCardsApi(apiClient: AxiosInstance) {
  return {
    /**
     * Get all cards in a deck.
     */
    async getCards(deckId: string): Promise<Card[]> {
      return handleApiCall(
        () => apiClient.get(`/decks/${deckId}/cards`),
        `Failed to fetch cards from deck ${deckId}`,
      );
    },

    /**
     * Get a specific card by ID.
     */
    async getCard(cardId: string): Promise<Card> {
      return handleApiCall(
        () => apiClient.get(`/cards/${cardId}`),
        `Failed to fetch card ${cardId}`,
      );
    },

    /**
     * Create a new card.
     */
    async createCard(payload: CreateCardPayload): Promise<Card> {
      return handleApiCall(() => apiClient.post('/cards', payload), 'Failed to create card');
    },

    /**
     * Update an existing card.
     */
    async updateCard(cardId: string, payload: UpdateCardPayload): Promise<Card> {
      return handleApiCall(
        () => apiClient.patch(`/cards/${cardId}`, payload),
        `Failed to update card ${cardId}`,
      );
    },

    /**
     * Delete a card.
     */
    async deleteCard(cardId: string): Promise<void> {
      return handleApiCall(
        () => apiClient.delete(`/cards/${cardId}`),
        `Failed to delete card ${cardId}`,
      );
    },
  };
}
