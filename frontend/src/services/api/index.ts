/**
 * Unified API client service for Mnemonic backend.
 * Provides type-safe HTTP communication with comprehensive error handling.
 * Follows "NO SILENT FAILURES" principle - all errors are explicit and informative.
 */

import { createApiClient, ApiClientError } from './client';
import { createAuthApi } from './auth';
import { createDecksApi } from './decks';
import { createCardsApi } from './cards';
import { createReviewsApi } from './reviews';

// Create the singleton API client instance
const apiClient = createApiClient();

/**
 * Unified API client for Mnemonic backend communication.
 * All methods throw ApiClientError on failure with descriptive messages.
 */
export const api = {
  ...createAuthApi(apiClient),
  ...createDecksApi(apiClient),
  ...createCardsApi(apiClient),
  ...createReviewsApi(apiClient),

  /**
   * Utility method to extract structured error info from any error.
   */
  getErrorInfo(error: unknown): { message: string; details?: unknown } {
    if (error instanceof ApiClientError) {
      return {
        message: error.message,
        details: error.details,
      };
    }
    if (error instanceof Error) {
      return {
        message: error.message,
      };
    }
    if (typeof error === 'string') {
      return {
        message: error,
      };
    }
    return {
      message: 'An unexpected error occurred',
    };
  },
};

/**
 * Export the axios instance for direct access if needed.
 * Prefer using the api object above for standard operations.
 */
export { ApiClientError };
export default apiClient;
