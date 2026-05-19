/**
 * Re-export from the unified API client.
 * The modular api/ structure has been replaced with a single flat client.
 */

export { api, ApiError, ApiError as ApiClientError } from '../api';
export { default } from '../api';
