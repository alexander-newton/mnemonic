/**
 * API client for Mnemonic backend.
 * Simple fetch-based client following the "NO SILENT FAILURES" principle.
 * All errors are explicit and informative.
 */

const BASE = import.meta.env.VITE_API_BASE ?? '/api';

/**
 * Custom error class for API failures.
 * Provides structured error information for UI error handling.
 */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'ApiError';
    Object.setPrototypeOf(this, ApiError.prototype);
  }

  /** Alias for status — kept for backward compat. */
  get statusCode(): number {
    return this.status;
  }
}

/**
 * Backward-compat alias for ApiError.
 * Older code imported ApiClientError; both refer to the same class.
 */
export class ApiClientError extends ApiError {
  constructor(
    status: number,
    message: string,
    details?: Record<string, unknown>,
  ) {
    super(status, message, details);
    this.name = 'ApiClientError';
    Object.setPrototypeOf(this, ApiClientError.prototype);
  }
}

/**
 * Internal fetch wrapper. Throws ApiError on non-ok responses.
 */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init);
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new ApiError(
      response.status,
      `${response.status}: ${detail || response.statusText}`,
    );
  }
  return response.json() as Promise<T>;
}

/**
 * Unified API client for Mnemonic backend communication.
 * All methods throw ApiError on failure with descriptive messages.
 */
export const api = {
  // ---- Decks ----

  /** List all decks. */
  listDecks: () => request<any[]>('/decks'),

  /** @deprecated Alias for listDecks kept for backward compat with useDecks hook. */
  getDecks: () => request<any[]>('/decks'),

  /** Get a single deck by folder slug or ID. */
  getDeck: (folder: string) => request<any>(`/decks/${folder}`),

  /** Create a new deck. */
  createDeck: (payload: object) =>
    request<any>('/decks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  /** Update an existing deck. */
  updateDeck: (id: string, payload: object) =>
    request<any>(`/decks/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  /** Delete a deck. */
  deleteDeck: (id: string) =>
    request<void>(`/decks/${id}`, { method: 'DELETE' }),

  // ---- Cards ----

  /** List cards, optionally filtered by deck. */
  listCards: (deck?: string) =>
    request<any[]>(`/cards${deck ? `?deck=${encodeURIComponent(deck)}` : ''}`),

  /** @deprecated Alias for listCards kept for backward compat with useCards hook. */
  getCards: (deckId: string) =>
    request<any[]>(`/decks/${deckId}/cards`),

  /** Get a single card by ID. */
  getCard: (id: string) => request<any>(`/cards/${id}`),

  /** Create a new card. */
  createCard: (payload: object) =>
    request<any>('/cards', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  /** Update an existing card. */
  updateCard: (id: string, payload: object) =>
    request<any>(`/cards/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  /** Delete a card. */
  deleteCard: (id: string) =>
    request<void>(`/cards/${id}`, { method: 'DELETE' }),

  // ---- Reviews ----

  /** Submit a card rating. */
  rate: (payload: { card_id: string; rating: number; response_time_ms: number }) =>
    request<{ ok: true }>('/reviews/rate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  /** @deprecated Alias for rate — kept for backward compat with setup.test.ts. */
  createReview: (payload: object) =>
    request<any>('/reviews', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  // ---- Misc ----

  /** Get usage statistics. */
  usage: () => request<any>('/usage'),

  /** Get vault status. */
  vaultStatus: () => request<any>('/vault/status'),

  /** Get application configuration. */
  getConfig: () => request<any>('/config'),

  /**
   * Utility method to extract structured error info from any error.
   * Kept for backward compat with setup.test.ts and existing consumers.
   */
  getErrorInfo(error: unknown): { message: string; details?: unknown } {
    if (error instanceof ApiError) {
      return { message: error.message, details: error.details };
    }
    if (error instanceof Error) {
      return { message: error.message };
    }
    if (typeof error === 'string') {
      return { message: error };
    }
    return { message: 'An unexpected error occurred' };
  },
};

export default api;
