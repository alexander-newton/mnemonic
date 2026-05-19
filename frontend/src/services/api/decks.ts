/**
 * Deck management API endpoints.
 */

import { AxiosInstance } from 'axios';
import { Deck, CreateDeckPayload, UpdateDeckPayload } from '@/types';
import { handleApiCall } from './client';

/**
 * Provides deck-related API methods.
 */
export function createDecksApi(apiClient: AxiosInstance) {
  return {
    /**
     * Get all decks for the current user.
     */
    async getDecks(): Promise<Deck[]> {
      return handleApiCall(() => apiClient.get('/decks'), 'Failed to fetch decks');
    },

    /**
     * Get a specific deck by ID.
     */
    async getDeck(deckId: string): Promise<Deck> {
      return handleApiCall(
        () => apiClient.get(`/decks/${deckId}`),
        `Failed to fetch deck ${deckId}`,
      );
    },

    /**
     * Create a new deck.
     */
    async createDeck(payload: CreateDeckPayload): Promise<Deck> {
      return handleApiCall(() => apiClient.post('/decks', payload), 'Failed to create deck');
    },

    /**
     * Update an existing deck.
     */
    async updateDeck(deckId: string, payload: UpdateDeckPayload): Promise<Deck> {
      return handleApiCall(
        () => apiClient.patch(`/decks/${deckId}`, payload),
        `Failed to update deck ${deckId}`,
      );
    },

    /**
     * Delete a deck.
     */
    async deleteDeck(deckId: string): Promise<void> {
      return handleApiCall(
        () => apiClient.delete(`/decks/${deckId}`),
        `Failed to delete deck ${deckId}`,
      );
    },
  };
}
