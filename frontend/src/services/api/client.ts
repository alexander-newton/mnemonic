/**
 * API client factory and error handling.
 * Creates and configures the axios instance for API communication.
 */

import axios, { AxiosInstance, AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { ApiError } from '@/types';

/**
 * Constants for API configuration
 */
const API_REQUEST_TIMEOUT_MS = 30000;
const DEFAULT_API_BASE_URL = 'http://localhost:8000';

/**
 * Custom error class for API-related failures.
 * Provides structured error information for UI error handling.
 */
export class ApiClientError extends Error {
  constructor(
    public readonly statusCode: number,
    public readonly message: string,
    public readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'ApiClientError';
    Object.setPrototypeOf(this, ApiClientError.prototype);
  }
}

/**
 * Creates and configures the axios instance for API communication.
 * Sets up interceptors for error handling and request/response transformation.
 */
export function createApiClient(): AxiosInstance {
  const baseURL = import.meta.env.VITE_API_URL || DEFAULT_API_BASE_URL;

  const client = axios.create({
    baseURL,
    timeout: API_REQUEST_TIMEOUT_MS,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Request interceptor for adding auth tokens in the future
  client.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      // TODO: Add authorization header when authentication is implemented
      // const token = localStorage.getItem('authToken');
      // if (token) {
      //   config.headers.Authorization = `Bearer ${token}`;
      // }
      return config;
    },
    (error: AxiosError) => {
      // Request setup failed - this is a client-side error
      const message = `Failed to prepare request: ${error.message}`;
      const apiError = new ApiClientError(0, message);
      return Promise.reject(apiError);
    },
  );

  // Response interceptor for error handling
  client.interceptors.response.use(
    (response: AxiosResponse) => response,
    (error: AxiosError<ApiError>) => {
      // Network error or timeout
      if (!error.response) {
        const message =
          error.code === 'ECONNABORTED'
            ? `Request timeout. Check your network connection and ensure the backend is running at ${baseURL}`
            : `Network error: ${error.message}. Ensure the backend is running at ${baseURL}`;
        const apiError = new ApiClientError(0, message);
        return Promise.reject(apiError);
      }

      // HTTP error response
      const { status, data } = error.response;
      let message = '';
      let details: Record<string, unknown> | undefined;

      if (data && typeof data === 'object' && 'message' in data) {
        message = (data as ApiError).message;
        details = (data as ApiError).details;
      } else {
        message = `HTTP ${status}: ${error.message}`;
      }

      // Add status-specific context
      if (status === 401) {
        message = `Unauthorized. Please check your credentials. ${message}`;
      } else if (status === 403) {
        message = `Permission denied. You do not have access to this resource. ${message}`;
      } else if (status === 404) {
        message = `Resource not found. ${message}`;
      } else if (status === 422) {
        message = `Invalid input. Please check your data. ${message}`;
      } else if (status >= 500) {
        message = `Server error. The backend service may be temporarily unavailable. ${message}`;
      }

      const apiError = new ApiClientError(status, message, details);
      return Promise.reject(apiError);
    },
  );

  return client;
}

/**
 * Helper function to handle API calls with consistent error handling.
 * Eliminates code duplication across all API methods.
 *
 * @param apiCall - The async function that makes the API call
 * @param errorMessage - The error message to use if an unexpected error occurs
 * @returns The response data
 * @throws ApiClientError if the call fails
 */
export async function handleApiCall<T>(
  apiCall: () => Promise<AxiosResponse<T>>,
  errorMessage: string,
): Promise<T> {
  try {
    const response = await apiCall();
    return response.data;
  } catch (error) {
    if (error instanceof ApiClientError) {
      throw error;
    }
    throw new ApiClientError(0, errorMessage);
  }
}
