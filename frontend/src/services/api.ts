/**
 * Re-export from modular API structure for backward compatibility.
 * The API client has been refactored into modules for better maintainability.
 * See the api/ directory for the implementation.
 */

export { api, ApiClientError, default as apiClient } from './api/index';
